"use client";

import { useMemo, useState } from "react";

const DEFAULT_BACKEND = "http://localhost:8000";
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const questionPool = [
  "미국 AI 행정명령의 핵심 골자를 한 문장으로 요약해줘.",
  "G7 히로시마 AI 프로세스 행동강령은 무엇을 요구했어?",
  "블레츨리 선언의 AI 안전 협력 내용은 뭐야?",
  "AI 생성 콘텐츠 표시와 워터마크 관련 조치를 설명해줘.",
  "첨단 AI 시스템 안전 테스트 계획의 주체와 목적을 알려줘.",
  "AI 분야 외국인 전문가 유치 지원 내용이 문서에 있어?",
  "AI 위험 평가와 완화에 대한 국제 행동강령 조치를 요약해줘.",
  "공공부문 역량 구축과 AI 안전 연구 협력 내용을 알려줘.",
];

async function readJsonResponse(res) {
  if (res.status === 204) return null;
  const text = await res.text();
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    return { raw: text };
  }
}

export default function Home() {
  const [backendUrl, setBackendUrl] = useState(DEFAULT_BACKEND);
  const [maxProcessNum, setMaxProcessNum] = useState(10);
  const [perUserCount, setPerUserCount] = useState(10);
  const [userDelayMs, setUserDelayMs] = useState(1000);
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState([]);
  const [status, setStatus] = useState(null);
  const [results, setResults] = useState([]);
  const [summary, setSummary] = useState(null);

  const expectedTotal = useMemo(() => perUserCount * 2, [perUserCount]);

  const appendLog = (message, data) => {
    setLog((prev) => [
      ...prev,
      {
        at: new Date().toLocaleTimeString(),
        message,
        data,
      },
    ]);
  };

  const request = async (path, options = {}) => {
    const res = await fetch(`${backendUrl}${path}`, options);
    const data = await readJsonResponse(res);
    if (!res.ok && res.status !== 204) {
      throw new Error(`${options.method || "GET"} ${path} ${res.status}: ${JSON.stringify(data)}`);
    }
    return { status: res.status, data };
  };

  const postJson = (path, body) =>
    request(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

  const refreshStatus = async () => {
    const { data } = await request("/test/status");
    setStatus(data);
    return data;
  };

  const bootstrap = async () => {
    setBusy(true);
    try {
      const { data: health } = await request("/health");
      setMaxProcessNum(health.maxProcessNum);
      setPerUserCount((current) => Math.max(current, 10));
      appendLog("health 확인", health);

      const { data } = await postJson("/test/bootstrap-save-users", {
        users: ["user1", "user2"],
      });
      appendLog("save/user1.json, save/user2.json 기반 Context/Chat 부트스트랩 완료", data);
      await refreshStatus();
    } catch (error) {
      appendLog("부트스트랩 실패", String(error));
    } finally {
      setBusy(false);
    }
  };

  const sendBurst = async ({ userId, sessionId, experimentId }) => {
    const started = performance.now();
    const jobs = Array.from({ length: perUserCount }, (_, index) => {
      const seq = index + 1;
      const requestId = `${experimentId}-${userId}-${seq}`;
      return postJson("/text", {
        userId,
        sessionId,
        seq,
        text: questionPool[index % questionPool.length],
        lang: "ko-KR",
        requestId,
      }).then(({ data }) => ({ requestId, data }));
    });
    const accepted = await Promise.all(jobs);
    appendLog(`${userId} ${accepted.length}개 요청 접수`, {
      acceptDurationSec: Number(((performance.now() - started) / 1000).toFixed(3)),
      requestIds: accepted.map((item) => item.requestId),
    });
    return accepted;
  };

  const runExperiment = async () => {
    setBusy(true);
    setLog([]);
    setResults([]);
    setSummary(null);
    try {
      await postJson("/test/reset-observability", {});
      const { data: health } = await request("/health");
      setMaxProcessNum(health.maxProcessNum);
      appendLog("실험 시작", {
        maxProcessNum: health.maxProcessNum,
        perUserCount,
        userDelayMs,
        expectedTotal,
      });

      await postJson("/test/bootstrap-save-users", { users: ["user1", "user2"] });
      appendLog("부트스트랩 확인 완료", "실제 OpenAI embeddings 기반 Context/Chat 사용");

      const experimentId = `web-${Date.now()}`;
      const accepted1 = await sendBurst({
        userId: "user1",
        sessionId: "saved-session-user1",
        experimentId,
      });
      await sleep(userDelayMs);
      const accepted2 = await sendBurst({
        userId: "user2",
        sessionId: "saved-session-user2",
        experimentId,
      });
      const expectedIds = new Set([...accepted1, ...accepted2].map((item) => item.requestId));
      const received = new Map();
      const startedPolling = Date.now();

      while (Date.now() - startedPolling < 240000 && received.size < expectedIds.size) {
        const annotations = await request("/callbacks/annotations");
        if (annotations.status !== 204 && annotations.data?.results) {
          for (const item of annotations.data.results) {
            if (expectedIds.has(item.requestId)) received.set(item.requestId, item);
          }
          setResults(Array.from(received.values()));
        }
        const nextStatus = await refreshStatus();
        appendLog("poll", {
          received: `${received.size}/${expectedIds.size}`,
          currentChatInputs: nextStatus.currentChatInputs,
          chatProcessQueue: nextStatus.chatProcessQueue,
          runningBackgroundBatches: nextStatus.runningBackgroundBatches,
        });
        if (received.size >= expectedIds.size) break;
        await sleep(5000);
      }

      const finalStatus = await refreshStatus();
      const scopedRequests = finalStatus.requestDetails.filter((item) => expectedIds.has(item.requestId));
      const latencies = scopedRequests.map((item) => item.totalLatencySec).filter(Number.isFinite);
      const nextSummary = {
        complete: received.size === expectedIds.size,
        receivedCount: received.size,
        totalRequests: expectedIds.size,
        batches: finalStatus.batches,
        latencySec: latencies.length
          ? {
              min: Math.min(...latencies),
              max: Math.max(...latencies),
              avg: Number((latencies.reduce((a, b) => a + b, 0) / latencies.length).toFixed(3)),
            }
          : null,
      };
      setSummary(nextSummary);
      appendLog("실험 종료", nextSummary);
    } catch (error) {
      appendLog("실험 실패", String(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">SpeakNote Queue / Coroutine Tester</p>
        <h1>2명 유저 동시 요청 배치 flush 실험</h1>
        <p>
          <code>save/user1.json</code>, <code>save/user2.json</code> 문서 객체를 서버에 로드한 뒤,
          10개 요청을 기준으로 큐 배치와 비동기 LLM 처리 결과를 관측합니다.
          CLI 스크립트는 단일 평균 처리시간과 1초 간격 반환 개선 여부도 함께 측정합니다.
        </p>
      </section>

      <section className="panel grid">
        <label>
          Backend URL
          <input value={backendUrl} onChange={(e) => setBackendUrl(e.target.value)} />
        </label>
        <label>
          MAX_PROCESS_NUM
          <input value={maxProcessNum} readOnly />
        </label>
        <label>
          유저당 요청 수(기본 10)
          <input
            type="number"
            min={1}
            value={perUserCount}
            onChange={(e) => setPerUserCount(Number(e.target.value))}
          />
        </label>
        <label>
          user1 → user2 간격(ms)
          <input type="number" value={userDelayMs} onChange={(e) => setUserDelayMs(Number(e.target.value))} />
        </label>
      </section>

      <section className="actions">
        <button disabled={busy} onClick={bootstrap}>1. 부트스트랩</button>
        <button disabled={busy} onClick={runExperiment}>2. 실험 실행</button>
        <button disabled={busy} onClick={refreshStatus}>상태 새로고침</button>
      </section>

      {summary && (
        <section className="panel">
          <h2>요약</h2>
          <pre>{JSON.stringify(summary, null, 2)}</pre>
        </section>
      )}

      <section className="columns">
        <div className="panel">
          <h2>Queue status</h2>
          <pre>{status ? JSON.stringify(status, null, 2) : "아직 상태 없음"}</pre>
        </div>
        <div className="panel">
          <h2>Annotations ({results.length}/{expectedTotal})</h2>
          <pre>{results.length ? JSON.stringify(results.slice(0, 6), null, 2) : "아직 결과 없음"}</pre>
        </div>
      </section>

      <section className="panel">
        <h2>실험 로그</h2>
        <ol className="log">
          {log.map((item, index) => (
            <li key={`${item.at}-${index}`}>
              <span>{item.at}</span>
              <strong>{item.message}</strong>
              {item.data !== undefined && <pre>{JSON.stringify(item.data, null, 2)}</pre>}
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}
