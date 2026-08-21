import asyncio
import json
import os
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from dotenv import load_dotenv

# .env must be loaded before importing speak_note modules because they construct
# LangChain/OpenAI clients at import time.
load_dotenv()

from fastapi import FastAPI, Form, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from langchain_core.documents import Document
from pydantic import BaseModel

# ---- 앱 내부 의존성: read/use only, do not edit speak_note/* ----
from speak_note.engine.app import App
from speak_note.instance.context import Context
from speak_note.manager.task_manager import ChatTask

# ===================== 앱/서버 초기화 =====================
app_backend = App()
app_backend.task_manager.max_process_num = int(os.getenv("MAX_PROCESS_NUM", "10"))
app_backend.task_manager.chat_patient = float(os.getenv("CHAT_PATIENT_SEC", app_backend.task_manager.chat_patient))
app = FastAPI(title="SpeakNote Backend", version="0.2.0-test-queue")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "./data").strip('"')
PORT_NUM = int(os.getenv("PORT_NUM", "8000"))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

_STATE_LOCK = threading.RLock()
REQUEST_STATE: Dict[str, Dict[str, Any]] = {}
BATCH_EVENTS: List[Dict[str, Any]] = []
_ORIGINAL_MULTIPLE_CHAT_INVOKE = app_backend.multiple_chat_invoke


# ===================== 모델 정의 =====================
class TextRequest(BaseModel):
    userId: str
    sessionId: str
    seq: int
    text: str
    lang: Optional[str] = "ko-KR"
    requestId: Optional[str] = None
    chatId: Optional[str] = None


class ContextRequest(BaseModel):
    userId: str
    sessionId: str
    fileId: str
    lang: Optional[str] = "ko-KR"


class BootstrapRequest(BaseModel):
    saveRoot: str = "save"
    users: Optional[List[str]] = None
    sessionPrefix: str = "saved-session"
    force: bool = False


class TestConfigRequest(BaseModel):
    maxProcessNum: Optional[int] = None
    chatPatientSec: Optional[float] = None


# ===================== 계측/큐 유틸 =====================
def _now() -> float:
    return time.time()


def _iso(ts: Optional[float] = None) -> str:
    return datetime.fromtimestamp(ts or _now()).isoformat(timespec="milliseconds")


def _body_dict(model: BaseModel) -> Dict[str, Any]:
    # Pydantic v1/v2 호환
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _queue_snapshot() -> Dict[str, Any]:
    tm = app_backend.task_manager
    with _STATE_LOCK:
        return {
            "maxProcessNum": tm.max_process_num,
            "chatPatientSec": tm.chat_patient,
            "contextPatientSec": tm.context_patient,
            "currentChatInputs": len(tm.current_chat_inputs),
            "chatProcessQueue": len(tm.chat_process_queue),
            "currentContextInputs": len(tm.current_context_inputs),
            "contextProcessQueue": len(tm.context_process_queue),
            "runningBackgroundBatches": len(app_backend.running_background_tasks),
            "requests": {
                "accepted": sum(1 for r in REQUEST_STATE.values() if r.get("status") == "queued"),
                "processing": sum(1 for r in REQUEST_STATE.values() if r.get("status") == "processing"),
                "completed": sum(1 for r in REQUEST_STATE.values() if r.get("status") == "completed"),
                "failed": sum(1 for r in REQUEST_STATE.values() if r.get("status") == "failed"),
                "total": len(REQUEST_STATE),
            },
            "batches": BATCH_EVENTS[-20:],
            "time": _iso(),
        }


def _enqueue_chat_payload(payload: Dict[str, Any]) -> bool:
    """Queue a raw /text payload using TaskManager's batching contract.

    speak_note.manager.task_manager.create_chat_task currently wraps items as
    {user_id: msg}, while App.multiple_chat_invoke expects each task itself to
    contain userId/sessionId/text. To keep speak_note/* untouched, server.py owns
    the adapter and still uses TaskManager's max_process_num/patient queues.
    Returns True if the call created a ready batch immediately.
    """
    tm = app_backend.task_manager
    now = _now()
    if not tm.current_chat_inputs:
        tm.last_chat_task_time = now

    tm.current_chat_inputs.append(payload)

    should_wait = (
        len(tm.current_chat_inputs) < tm.max_process_num
        and (now - tm.last_chat_task_time) < tm.chat_patient
    )
    if should_wait:
        return False

    chat_task = ChatTask(list(tm.current_chat_inputs))
    tm.chat_process_queue.append(chat_task)
    tm.current_chat_inputs.clear()
    tm.last_chat_task_time = None
    return True


def _flush_chat_now(reason: str = "manual") -> Dict[str, Any]:
    tm = app_backend.task_manager
    if not tm.current_chat_inputs:
        return {"flushed": False, "reason": reason, "batchSize": 0, "queue": _queue_snapshot()}

    batch_size = len(tm.current_chat_inputs)
    chat_task = ChatTask(list(tm.current_chat_inputs))
    tm.chat_process_queue.append(chat_task)
    tm.current_chat_inputs.clear()
    tm.last_chat_task_time = None
    return {"flushed": True, "reason": reason, "batchSize": batch_size, "queue": _queue_snapshot()}


async def _instrumented_multiple_chat_invoke(tasks: List[Dict[str, Any]]):
    batch_id = f"batch-{len(BATCH_EVENTS) + 1}-{uuid.uuid4().hex[:8]}"
    start = _now()
    request_ids = [task.get("requestId") for task in tasks]

    event: Dict[str, Any] = {
        "batchId": batch_id,
        "size": len(tasks),
        "requestIds": request_ids,
        "userIds": [task.get("userId") for task in tasks],
        "seqs": [task.get("seq") for task in tasks],
        "startedAt": _iso(start),
        "status": "processing",
    }
    with _STATE_LOCK:
        BATCH_EVENTS.append(event)
        for task in tasks:
            rid = task.get("requestId")
            if rid and rid in REQUEST_STATE:
                REQUEST_STATE[rid].update(
                    {
                        "status": "processing",
                        "batchId": batch_id,
                        "batchStartedAt": start,
                        "queueWaitSec": round(start - REQUEST_STATE[rid]["acceptedAt"], 3),
                    }
                )

    try:
        messages = await _ORIGINAL_MULTIPLE_CHAT_INVOKE(tasks)
        end = _now()
        result_by_request = {
            getattr(msg, "request_id", None): msg for msg in messages if getattr(msg, "request_id", None)
        }
        with _STATE_LOCK:
            event.update(
                {
                    "status": "completed",
                    "completedAt": _iso(end),
                    "durationSec": round(end - start, 3),
                    "completedCount": len(messages),
                }
            )
            for task in tasks:
                rid = task.get("requestId")
                if not rid or rid not in REQUEST_STATE:
                    continue
                msg = result_by_request.get(rid)
                if msg is None:
                    REQUEST_STATE[rid].update(
                        {
                            "status": "failed",
                            "completedAt": end,
                            "error": "message_not_returned_from_batch",
                        }
                    )
                else:
                    REQUEST_STATE[rid].update(
                        {
                            "status": "completed",
                            "completedAt": end,
                            "completedAtIso": _iso(end),
                            "totalLatencySec": round(end - REQUEST_STATE[rid]["acceptedAt"], 3),
                            "processingDurationSec": round(end - start, 3),
                            "jobId": msg.id,
                            "annotationChars": len(getattr(msg, "annotation", "") or ""),
                            "answerState": getattr(msg, "answerState", None),
                        }
                    )
        return messages
    except Exception as e:
        end = _now()
        with _STATE_LOCK:
            event.update(
                {
                    "status": "failed",
                    "completedAt": _iso(end),
                    "durationSec": round(end - start, 3),
                    "error": f"{type(e).__name__}: {e}",
                }
            )
            for rid in request_ids:
                if rid and rid in REQUEST_STATE:
                    REQUEST_STATE[rid].update(
                        {
                            "status": "failed",
                            "completedAt": end,
                            "totalLatencySec": round(end - REQUEST_STATE[rid]["acceptedAt"], 3),
                            "error": f"{type(e).__name__}: {e}",
                        }
                    )
        raise


app_backend.multiple_chat_invoke = _instrumented_multiple_chat_invoke


# ===================== 백그라운드 워커 =====================
def start_chat_worker():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print("[ChatWorker] 시작됨")
    try:
        loop.run_until_complete(app_backend.chats_background_worker())
    finally:
        loop.close()


def start_docs_worker():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print("[DocsWorker] 시작됨")
    try:
        loop.run_until_complete(app_backend.docs_background_worker())
    finally:
        loop.close()


@app.on_event("startup")
async def startup_event():
    threading.Thread(target=start_chat_worker, daemon=True).start()
    threading.Thread(target=start_docs_worker, daemon=True).start()
    print("[startup_event] Background workers started")


# ===================== 문서/유저 부트스트랩 =====================
def _save_upload_file(upload: UploadFile, save_dir: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    base = os.path.basename(upload.filename) if upload.filename else "uploaded.pdf"
    save_name = f"{ts}_{base}"
    save_path = os.path.join(save_dir, save_name)
    with open(save_path, "wb") as f:
        f.write(upload.file.read())
    return save_path


def _load_saved_user_context(user_id: str, save_root: str, session_id: str, force: bool = False) -> Dict[str, Any]:
    user = app_backend.user_manager.find_instance(user_id)
    if user is None:
        user = app_backend.user_manager.create_user(user_id=user_id)

    if user.chats and not force:
        return {
            "userId": user_id,
            "sessionId": getattr(user.contexts[-1], "id", session_id) if user.contexts else session_id,
            "chatId": user.chats[-1].id,
            "status": "already_loaded",
        }

    json_path = Path(save_root) / f"{user_id}.json"
    if not json_path.exists():
        raise FileNotFoundError(f"saved user json not found: {json_path}")

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    docs = [
        Document(page_content=text, metadata={"page": i + 1, "source": str(json_path)})
        for i, text in enumerate(data.get("document", []))
    ]
    if not docs:
        raise ValueError(f"no document entries in {json_path}")

    keywords = data.get("keywords") or ["saved-json", user_id]
    summary = data.get("summarize") or data.get("summary") or ""

    # This constructs OpenAI embeddings and the RAG retriever: it is intentionally
    # an actual LLM/API-backed setup, not a fallback smoke test.
    context = Context(
        session_id=session_id,
        document=docs,
        user_id=user_id,
        summary=summary,
        keywords=keywords,
    )
    app_backend.context_manager.create_instance(context)
    chat = app_backend.chat_manager.create_chat(user_id=user_id, context=context)
    user.contexts.append(context)
    user.chats.append(chat)

    return {
        "userId": user_id,
        "sessionId": context.id,
        "chatId": chat.id,
        "documentCount": len(docs),
        "summaryChars": len(summary),
        "status": "loaded",
    }


# ===================== 라우트 =====================
@app.get("/health")
async def health():
    return {"ok": True, **_queue_snapshot()}


@app.post("/test/bootstrap-save-users")
async def bootstrap_save_users(body: BootstrapRequest = BootstrapRequest()):
    save_root = Path(body.saveRoot)
    if body.users:
        users = body.users
    else:
        users = sorted(path.stem for path in save_root.glob("user*.json"))
    if not users:
        raise HTTPException(status_code=400, detail=f"No user json files found under {save_root}")

    started = _now()
    loaded = []
    for user_id in users:
        try:
            loaded.append(
                _load_saved_user_context(
                    user_id=user_id,
                    save_root=str(save_root),
                    session_id=f"{body.sessionPrefix}-{user_id}",
                    force=body.force,
                )
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"{user_id} bootstrap failed: {type(e).__name__}: {e}")

    return {
        "ok": True,
        "loaded": loaded,
        "durationSec": round(_now() - started, 3),
        "note": "save/*.json 문서를 OpenAI embeddings 기반 Context/Chat으로 로드했습니다.",
    }


@app.get("/test/status")
async def test_status():
    with _STATE_LOCK:
        requests = list(REQUEST_STATE.values())[-500:]
    return {**_queue_snapshot(), "requestDetails": requests}


@app.post("/test/config")
async def test_config(body: TestConfigRequest):
    tm = app_backend.task_manager
    if body.maxProcessNum is not None:
        if body.maxProcessNum < 1:
            raise HTTPException(status_code=400, detail="maxProcessNum must be >= 1")
        tm.max_process_num = body.maxProcessNum
    if body.chatPatientSec is not None:
        if body.chatPatientSec <= 0:
            raise HTTPException(status_code=400, detail="chatPatientSec must be > 0")
        tm.chat_patient = body.chatPatientSec
    return {"ok": True, **_queue_snapshot()}


@app.post("/test/flush-chat-now")
async def flush_chat_now():
    return _flush_chat_now("manual-api")


@app.post("/test/reset-observability")
async def reset_observability():
    tm = app_backend.task_manager
    with _STATE_LOCK:
        REQUEST_STATE.clear()
        BATCH_EVENTS.clear()
        tm.current_chat_inputs.clear()
        tm.chat_process_queue.clear()
        tm.last_chat_task_time = None
    return {"ok": True, "time": _iso(), "queue": _queue_snapshot()}


@app.post("/pdf")
async def handle_pdf(
    file: UploadFile = File(...),
    userId: str = Form(...),
    fileId: Optional[str] = Form(None),
    session_id: str = Form(...),
):
    user = app_backend.user_manager.find_instance(userId)
    if user is None:
        user = app_backend.user_manager.create_user(user_id=userId)

    try:
        saved_path = _save_upload_file(file, UPLOAD_FOLDER)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 실패: {e}")

    try:
        app_backend.task_manager.create_context_task(
            user_id=user.id, docs_path=saved_path, session_id=session_id
        )
        print(f"[PDF] ContextTask 등록됨: user={userId}, session={session_id}, path={saved_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"컨텍스트 작업 등록 실패: {e}")

    return JSONResponse(
        {
            "ok": True,
            "userId": userId,
            "fileId": fileId,
            "sessionID": session_id,
            "queue": _queue_snapshot(),
        },
        status_code=202,
    )


@app.post("/text")
async def handle_text(body: TextRequest):
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=400, detail="질문(text)이 비어 있습니다.")

    user = app_backend.user_manager.find_instance(body.userId)
    if user is None:
        raise HTTPException(
            status_code=400,
            detail="해당 유저가 없습니다. /test/bootstrap-save-users 또는 /pdf 업로드로 컨텍스트부터 생성하세요.",
        )
    if not getattr(user, "chats", None):
        raise HTTPException(
            status_code=400,
            detail="해당 유저의 Chat이 없습니다. /test/bootstrap-save-users 또는 /pdf 업로드로 컨텍스트부터 생성하세요.",
        )

    payload = _body_dict(body)
    payload["requestId"] = payload.get("requestId") or f"req-{uuid.uuid4()}"
    payload["text"] = payload["text"].strip()

    accepted_at = _now()
    with _STATE_LOCK:
        REQUEST_STATE[payload["requestId"]] = {
            "requestId": payload["requestId"],
            "userId": payload["userId"],
            "sessionId": payload["sessionId"],
            "seq": payload["seq"],
            "status": "queued",
            "acceptedAt": accepted_at,
            "acceptedAtIso": _iso(accepted_at),
        }

    flushedNow = _enqueue_chat_payload(payload)

    return JSONResponse(
        {
            "success": True,
            "status": "queued",
            "requestId": payload["requestId"],
            "sessionId": payload["sessionId"],
            "seq": payload["seq"],
            "flushedNow": flushedNow,
            "queue": _queue_snapshot(),
        },
        status_code=202,
    )


def _pop_annotations_response():
    result = app_backend.message_manager.pop_all_finished()
    total = result.get("totalNum", 0)
    if total == 0:
        return Response(status_code=204)
    return JSONResponse(result, status_code=200)


@app.get("/callbacks/annotations")
async def get_annotations():
    return _pop_annotations_response()


@app.post("/callbacks/annotations")
async def post_annotations():
    return _pop_annotations_response()


@app.get("/callbacks/contexts")
async def get_contexts():
    outputs = []
    while app_backend.context_output_list:
        outputs.append(app_backend.context_output_list.pop(0))
    if not outputs:
        return Response(status_code=204)
    return JSONResponse({"totalNum": len(outputs), "contexts": outputs}, status_code=200)


@app.post("/callbacks/contexts")
async def post_contexts():
    return await get_contexts()


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=PORT_NUM, reload=False)
