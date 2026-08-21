'''
main.py 에서는 아래 input만 취급하게 api 단순화한다.
main.py에서 리스트로 모으거나, 비동기 코딩을 하지 않게한다.
main.py에서는 프런트 서버와 실시간으로 소통하는 부분이다.

1. user_id
2. doc_path
3. msg

'''
#### 앞으로는 변수명을 조금 더 이쁘게 해보자. context면 그게 작업인지, 객체인지 딱정하고!, chat_task가 채팅을 만드는건지 단일 문장처리인지도 구분좀 하자..
from speak_note.manager.chat_manager import ChatManager
from speak_note.manager.context_manager import ContextManager
from speak_note.manager.user_manager import UserManager
from speak_note.manager.task_manager import TaskManager # 추가부분
from speak_note.manager.message_manager import MesseageManager
from speak_note.instance.message import Message

from flask import Flask, request, jsonify
import asyncio
import time

class App:
    def __init__(self, batch_concurrency=3):
        self.user_manager = UserManager()
        self.context_manager = ContextManager()
        self.chat_manager = ChatManager()
        self.task_manager = TaskManager()   

        self.message_manager = MesseageManager()    # 추가부분

        self.background_interval = 1  # 1초마다 큐 체크
        self.chat_lists = []          # 추가부분
        self.reps_list = []           # 결과받을 리스트 추가.

        self.context_output_list = []   # 추가부분
        self.running_background_tasks = set()   # 실행 중인 background batch task 참조 유지
        self.batch_concurrency = batch_concurrency
        self.batch_semaphore = asyncio.Semaphore(batch_concurrency)

    async def _run_with_semaphore(self, coro):
        async with self.batch_semaphore:
            return await coro
    
    def _create_background_task(self, coro):
        """
        coroutine을 background task로 실행한다.

        - batch 완료를 기다리지 않고 즉시 반환
        - 실행 중 task 참조 유지
        - 완료되면 자동 제거
        - task 내부 예외 확인
        """
        task = asyncio.create_task(coro)

        self.running_background_tasks.add(task)

        task.add_done_callback(self.running_background_tasks.discard)
        task.add_done_callback(self._handle_background_task_result)

        return task


    def _handle_background_task_result(self, task):
        """
        create_task 내부에서 발생한 예외가 조용히 묻히지 않도록 확인한다.
        """
        try:
            task.result()

        except asyncio.CancelledError:
            pass

        except Exception as e:
            print(f"[Background Batch Error] {e}")


    def create_user(self, user_info=None):
        # user_info(dict): 확장 가능. 예: {"name":..., ...}
        user = self.user_manager.create_user()
        return user

    # 여기서는 patient 이제 필요없음.
    '''
    # 수정전
    context_tasks = [
        {"user_id": user1.id, "docs_path": "./data/sample_AI_Brief.pdf"},
        {"user_id": user2.id, "docs_path": "./data/sample_AI_Brief.pdf"}
    ]

    # 수정후
    context_tasks = [
        {"user_id": user1.id, "session_id": "u1", "docs_path": "./data/sample_AI_Brief.pdf"},
        {"user_id": user2.id, "session_id": "u2", "docs_path": "./data/sample_AI_Brief.pdf"}
    ]
    '''
##################################################
# app.py 원본파일. 
##################################################    
    # async def create_chats(self, tasks):
    #     '''
    #     1. Context 여러개를 비동기로 생성 (context_manager 사용)
    #     2. 각 context마다 채팅(chat) 객체 생성 (chat_manager 사용)
    #     3. user_manager 통해서 유저에 context, chat 등록
    #     '''
    #     # 1. contexts = self.context_manager.create_context(tasks)  # 반환값: List[Context]
    #     contexts = await self.context_manager.create_context(tasks)

    #     # 2. tasks, contexts 매핑
    #     chats = []
    #     for task, context in zip(tasks, contexts):
    #         user_id = task["user_id"]   # 
    #         session_id = task["session_id"]
    #         # 3. chat 생성 및 매니저에 등록
    #         chat = self.chat_manager.create_chat(user_id=user_id, context=context, session_id = session_id)
    #         chats.append(chat)
    #         # 4. 유저에 등록
    #         user = self.user_manager.find_instance(user_id)
    #         if user:
    #             user.chats.append(chat)
    #             user.contexts.append(context)
    #     return chats
    
##################################################
# app.py 수정안. taskas에서 session_id 처리로직 추가.
##################################################
    async def create_chats(self, tasks):
        '''
        1. Context 여러개를 비동기로 생성 (context_manager 사용)
        2. 각 context마다 채팅(chat) 객체 생성 (chat_manager 사용)
        3. user_manager 통해서 유저에 context, chat 등록
        4. 생성된 context를 JSON 형식으로 변환해 context_output_list에 쌓음
        '''
        # 1. 실제 문서 전처리 및 Context 문서 생성
        contexts = await self.context_manager.create_context(tasks)

        chats = []
        for task, context in zip(tasks, contexts):
            user_id = task["user_id"]
            session_id = task["session_id"]

            # 2. Chat 생성 및 매니저 등록
            chat = self.chat_manager.create_chat(
                user_id=user_id,
                context=context,
            )
            chats.append(chat)

            # 3. 유저에 등록
            user = self.user_manager.find_instance(user_id)
            if user:
                user.chats.append(chat)
                user.contexts.append(context)

            # 4. Context → JSON 변환 후 저장
            context_output_json = self.to_context_json(context)
            self.context_output_list.append(context_output_json)

        return chats

    def to_context_json(self, context):
        """
        Context 객체를 API 응답용 JSON(dict)으로 변환
        """
        return {
            "success": True,
            "userID" : context.user_id,
            "sessionId": context.id,   # session_id를 id로 사용 중
            "summary": context.summary,
            "keywords": context.keywords,
        }

        
    '''
    # 수정전,
    chat_tasks = [
        {chat_list[1].id: "적분의 기본정리(FTC)를 설명해줘."},
        {chat_list[0].id: "G7은 AI에 대해서 어떤 합의를 했지?"},
    ]

    # 수정후,
    chat_tasks = [
        {
        "userId" : 1,
        "sessionId": "sess_A",       // 자바 세션과 1:1 매핑되는 식별자
        "seq": 137,                  // 세션 내 단조증가 시퀀스(주석 스냅샷 번호)
        "text": "STT 누적 텍스트 내용",  // 주석 생성 대상 텍스트(스냅샷)
        "lang": "ko-KR",
        "requestId": "uuid-req-1"    // 같은 작업의 중복 제출을 방지하는 키 (멱등키)
        },
        {
        "userId" : 1,
        "sessionId": "sess_A",       // 자바 세션과 1:1 매핑되는 식별자
        "seq": 137,                  // 세션 내 단조증가 시퀀스(주석 스냅샷 번호)
        "text": "STT 누적 텍스트 내용",  // 주석 생성 대상 텍스트(스냅샷)
        "lang": "ko-KR",
        "requestId": "uuid-req-1"    // 같은 작업의 중복 제출을 방지하는 키 (멱등키)
        },
    ]
    '''
    async def multiple_chat_invoke(self, tasks: list[dict]):
        """
        tasks = [
            {
            "userId": "user1",
            "sessionId": "sess_A",
            "seq": 137,
            "text": "STT 누적 텍스트 내용",
            "lang": "ko-KR",
            "requestId": "uuid-req-1"
            },
            ...
        ]
        """
        messages: list[Message] = []

        for task in tasks:
            user_id = task["userId"]
            user = self.user_manager.find_instance(user_id)
            if not user:
                print(f"User {user_id} not found, skip this request.")
                continue

            # 유저의 마지막 Chat 객체 가져오기
            if not user.chats:
                print(f"User {user_id} has no chats, skip this request.")
                continue
            chat_id = user.chats[-1].id

            # Message 객체 생성
            msg = Message(user_id=user_id, chat_id=chat_id)
            msg.get_request(task)

            # message_manager에 등록
            self.message_manager.create_instance(msg)
            messages.append(msg)

        # 비동기 채팅 실행 (ChatManager가 내부적으로 Chat.ainvoke 호출)
        results = await self.chat_manager.multiple_chat_invoke(messages)

        # 결과를 Message 객체에 반영
        for msg, result in zip(messages, results):
            msg.get_annotation(result)

            # user에도 기록
            user_id = getattr(msg, "user_id", None)
            if user_id:
                user = self.user_manager.find_instance(user_id)
                if user:
                    user.chat_history.append(msg)

        self.reps_list.extend(messages)
        return messages

####################################################################################################
    async def chats_background_worker(self):
        print("[Chat Background Worker] 대기 시작")

        while True:
            try:
                # patient 초과 task flush
                flushed_chat = self.task_manager.flush_chat_if_due()

                if flushed_chat:
                    print("[flush] patient 초과로 chat task 강제 flush됨")

                # queue에 준비된 batch 모두 dispatch
                while self.task_manager.is_chat_process_queue_available():

                    chat_tasks = self.task_manager.get_chat_task()

                    print(
                        "[Chat Background Worker] batch dequeued:",
                        chat_tasks
                    )

                    # 핵심:
                    # 현재 batch 완료를 기다리지 않고 event loop에 등록
                    self._create_background_task(
                        self._run_with_semaphore(
                            self.multiple_chat_invoke(chat_tasks)
                        )
                    )

            except Exception as e:
                print(f"[chat_background_worker Error] {e}")

            await asyncio.sleep(self.background_interval)

    def start_chat_worker(self):
        asyncio.create_task(self.chats_background_worker())

    
    # app에 reps list를 추가해서, 해당리스트가 차있으면 매번 빼서 프런트서버로 연결해준다.
    async def docs_background_worker(self):
        print("[Docs Background Worker] 대기 시작")

        while True:
            try:
                # patient 초과 task flush
                flushed_context = self.task_manager.flush_context_if_due()

                if flushed_context:
                    print("[flush] patient 초과로 context task 강제 flush됨")

                # queue에 준비된 batch 모두 dispatch
                while self.task_manager.is_context_process_queue_available():

                    context_tasks = self.task_manager.get_context_task()

                    print(
                        "[Docs Background Worker] batch dequeued:",
                        context_tasks
                    )

                    # 현재 batch 완료를 기다리지 않고 실행
                    self._create_background_task(
                        self._run_with_semaphore(
                            self.multiple_chat_invoke(context_tasks)
                        )
                    )

            except Exception as e:
                print(f"[docs_background_worker Error] {e}")

            await asyncio.sleep(self.background_interval)

    def start_docs_worker(self):
        asyncio.create_task(self.docs_background_worker())