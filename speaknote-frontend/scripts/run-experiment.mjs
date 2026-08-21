const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
const TEST_REQUEST_COUNT = Number(process.env.TEST_REQUEST_COUNT || 10);
const REQUEST_INTERVAL_MS = Number(process.env.REQUEST_INTERVAL_MS || 1000);
const SINGLE_RUNS = Number(process.env.SINGLE_RUNS || 3);
const POLL_INTERVAL_MS = Number(process.env.POLL_INTERVAL_MS || 500);
const TIMEOUT_MS = Number(process.env.TIMEOUT_MS || 300000);
const DEFAULT_MAX_PROCESS_NUM = Number(process.env.MAX_PROCESS_NUM || 10);

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function request(path, options = {}) {
  const res = await fetch(`${BACKEND_URL}${path}`, options);
  if (res.status === 204) return { status: 204, data: null };
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }
  if (!res.ok) {
    throw new Error(`${options.method || 'GET'} ${path} failed: ${res.status} ${JSON.stringify(data)}`);
  }
  return { status: res.status, data };
}

async function postJson(path, body = {}) {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

const questionPool = [
  '미국 AI 행정명령의 핵심 골자를 한 문장으로 요약해줘.',
  'G7 히로시마 AI 프로세스 행동강령은 무엇을 요구했어?',
  '블레츨리 선언의 AI 안전 협력 내용은 뭐야?',
  'AI 생성 콘텐츠 표시와 워터마크 관련 조치를 설명해줘.',
  '첨단 AI 시스템 안전 테스트 계획의 주체와 목적을 알려줘.',
  'AI 분야 외국인 전문가 유치 지원 내용이 문서에 있어?',
  'AI 위험 평가와 완화에 대한 국제 행동강령 조치를 요약해줘.',
  '공공부문 역량 구축과 AI 안전 연구 협력 내용을 알려줘.',
  '첨단 AI 개발 기업의 투명성 향상 조치를 설명해줘.',
  '국제 기술 표준 개발과 개인정보 보호 조치를 요약해줘.',
];

function avg(values) {
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
}

function round(value, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  return Number(value.toFixed(digits));
}

function percentile(values, p) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.min(sorted.length - 1, Math.max(0, Math.ceil((p / 100) * sorted.length) - 1));
  return sorted[idx];
}

async function configure(maxProcessNum, chatPatientSec = 3) {
  const { data } = await postJson('/test/config', { maxProcessNum, chatPatientSec });
  return data;
}

async function reset() {
  await postJson('/test/reset-observability', {});
}

async function bootstrap() {
  return (await postJson('/test/bootstrap-save-users', { users: ['user1', 'user2'] })).data;
}

async function sendText({ userId, sessionId, seq, requestId, text }) {
  const acceptedAtMs = Date.now();
  const { data } = await postJson('/text', {
    userId,
    sessionId,
    seq,
    text,
    lang: 'ko-KR',
    requestId,
  });
  return { requestId, acceptedAtMs, accepted: data };
}

async function pollStatusUntilComplete(expectedIds, label) {
  const expected = new Set(expectedIds);
  const started = Date.now();
  let lastStatus = null;

  while (Date.now() - started < TIMEOUT_MS) {
    lastStatus = (await request('/test/status')).data;
    const scoped = lastStatus.requestDetails.filter((item) => expected.has(item.requestId));
    const completed = scoped.filter((item) => item.status === 'completed');
    const failed = scoped.filter((item) => item.status === 'failed');
    console.log(
      `[${label}] completed=${completed.length}/${expected.size}, failed=${failed.length}, queued=${lastStatus.currentChatInputs}, processQueue=${lastStatus.chatProcessQueue}, running=${lastStatus.runningBackgroundBatches}`
    );
    if (completed.length + failed.length >= expected.size) {
      return { status: lastStatus, scoped, completed, failed, complete: failed.length === 0 && completed.length === expected.size };
    }
    await sleep(POLL_INTERVAL_MS);
  }

  lastStatus = lastStatus || (await request('/test/status')).data;
  const scoped = lastStatus.requestDetails.filter((item) => expected.has(item.requestId));
  return {
    status: lastStatus,
    scoped,
    completed: scoped.filter((item) => item.status === 'completed'),
    failed: scoped.filter((item) => item.status === 'failed'),
    complete: false,
    timeout: true,
  };
}

async function drainAnnotations(expectedIds) {
  const expected = new Set(expectedIds);
  const received = new Map();
  for (let i = 0; i < 10 && received.size < expected.size; i += 1) {
    const annotations = await request('/callbacks/annotations');
    if (annotations.status !== 204 && annotations.data?.results) {
      for (const item of annotations.data.results) {
        if (expected.has(item.requestId)) received.set(item.requestId, item);
      }
    }
    if (received.size < expected.size) await sleep(250);
  }
  return Array.from(received.values());
}

async function measureSingleRequestAverage() {
  await reset();
  await configure(1, 30);
  const processing = [];
  const totals = [];
  const ids = [];

  for (let i = 1; i <= SINGLE_RUNS; i += 1) {
    const requestId = `single-${Date.now()}-${i}`;
    ids.push(requestId);
    console.log(`[single] run=${i}/${SINGLE_RUNS}`);
    await sendText({
      userId: 'user1',
      sessionId: 'saved-session-user1',
      seq: i,
      requestId,
      text: questionPool[(i - 1) % questionPool.length],
    });
    // maxProcessNum=1 should flush immediately, but this is harmless and makes intent explicit.
    await postJson('/test/flush-chat-now', {});
    const result = await pollStatusUntilComplete([requestId], `single-${i}`);
    const item = result.completed[0];
    if (!item) throw new Error(`single run ${i} did not complete: ${JSON.stringify(result.failed)}`);
    processing.push(item.processingDurationSec);
    totals.push(item.totalLatencySec);
  }

  await drainAnnotations(ids);
  return {
    runs: SINGLE_RUNS,
    requestIds: ids,
    processingDurationSec: {
      values: processing,
      avg: round(avg(processing)),
      min: round(Math.min(...processing)),
      max: round(Math.max(...processing)),
      p50: round(percentile(processing, 50)),
      p90: round(percentile(processing, 90)),
    },
    totalLatencySec: {
      values: totals,
      avg: round(avg(totals)),
      min: round(Math.min(...totals)),
      max: round(Math.max(...totals)),
    },
  };
}

async function measureIntervalRealtime(singleAverageSec) {
  await reset();
  await configure(1, 30);
  const experimentId = `interval-${Date.now()}`;
  const accepted = [];

  for (let i = 1; i <= TEST_REQUEST_COUNT; i += 1) {
    const requestId = `${experimentId}-${i}`;
    const item = await sendText({
      userId: 'user1',
      sessionId: 'saved-session-user1',
      seq: i,
      requestId,
      text: questionPool[(i - 1) % questionPool.length],
    });
    accepted.push({ ...item, seq: i });
    console.log(`[interval] sent seq=${i}/${TEST_REQUEST_COUNT}, requestId=${requestId}`);
    if (i < TEST_REQUEST_COUNT) await sleep(REQUEST_INTERVAL_MS);
  }

  const ids = accepted.map((item) => item.requestId);
  const result = await pollStatusUntilComplete(ids, 'interval');
  await drainAnnotations(ids);

  const acceptedById = new Map(accepted.map((item) => [item.requestId, item]));
  const firstAcceptedMs = Math.min(...accepted.map((item) => item.acceptedAtMs));
  const completionsBySeq = result.completed
    .map((item) => ({
      seq: acceptedById.get(item.requestId)?.seq,
      requestId: item.requestId,
      acceptedOffsetSec: round((acceptedById.get(item.requestId).acceptedAtMs - firstAcceptedMs) / 1000),
      completedOffsetSec: round((new Date(item.completedAtIso).getTime() - firstAcceptedMs) / 1000),
      totalLatencySec: item.totalLatencySec,
      processingDurationSec: item.processingDurationSec,
    }))
    .sort((a, b) => a.seq - b.seq);

  // 반환 간격은 seq 순서가 아니라 실제 completion event 시간순으로 계산한다.
  // 비동기 처리에서는 후속 요청이 앞선 요청보다 먼저 끝날 수 있기 때문이다.
  const completionEvents = [...completionsBySeq].sort((a, b) => a.completedOffsetSec - b.completedOffsetSec);

  const completionGaps = [];
  for (let i = 1; i < completionEvents.length; i += 1) {
    completionGaps.push(round(completionEvents[i].completedOffsetSec - completionEvents[i - 1].completedOffsetSec));
  }

  const avgGap = avg(completionGaps);
  const intervalSec = REQUEST_INTERVAL_MS / 1000;
  const improvedVsSequential = singleAverageSec ? avgGap < singleAverageSec * 0.6 : null;
  const followsRequestInterval = avgGap !== null ? avgGap <= Math.max(intervalSec * 3, intervalSec + 2) : null;

  return {
    requestCount: TEST_REQUEST_COUNT,
    requestIntervalMs: REQUEST_INTERVAL_MS,
    complete: result.complete,
    failed: result.failed,
    firstCompletionOffsetSec: completionEvents[0]?.completedOffsetSec ?? null,
    completionGapsSec: completionGaps,
    avgCompletionGapSec: round(avgGap),
    maxCompletionGapSec: completionGaps.length ? round(Math.max(...completionGaps)) : null,
    singleAverageProcessingSec: singleAverageSec,
    improvedVsSequential,
    followsRequestInterval,
    verdict:
      improvedVsSequential && followsRequestInterval
        ? 'PASS: 첫 응답 이후 반환 간격이 단일 처리시간보다 훨씬 짧고 요청 간격에 근접함'
        : 'CHECK: batch/worker/API 지연으로 반환 간격 개선 여부 재확인 필요',
    completionEvents,
    completionsBySeq,
  };
}

async function measureBatchFlush10() {
  await reset();
  await configure(DEFAULT_MAX_PROCESS_NUM, 3);
  const experimentId = `batch10-${Date.now()}`;
  const sends = [];
  for (let i = 1; i <= TEST_REQUEST_COUNT; i += 1) {
    sends.push(
      sendText({
        userId: i % 2 ? 'user1' : 'user2',
        sessionId: i % 2 ? 'saved-session-user1' : 'saved-session-user2',
        seq: i,
        requestId: `${experimentId}-${i}`,
        text: questionPool[(i - 1) % questionPool.length],
      })
    );
  }
  const accepted = await Promise.all(sends);
  const ids = accepted.map((item) => item.requestId);
  const result = await pollStatusUntilComplete(ids, 'batch10');
  await drainAnnotations(ids);
  const matchingBatches = result.status.batches.filter((batch) => batch.requestIds?.some((id) => ids.includes(id)));
  return {
    maxProcessNum: DEFAULT_MAX_PROCESS_NUM,
    requestCount: TEST_REQUEST_COUNT,
    complete: result.complete,
    batches: matchingBatches,
    expected: TEST_REQUEST_COUNT >= DEFAULT_MAX_PROCESS_NUM ? `첫 batch size가 ${DEFAULT_MAX_PROCESS_NUM}이면 max 도달 flush 확인` : null,
  };
}

async function main() {
  const startedAt = new Date().toISOString();
  console.log(`[experiment] backend=${BACKEND_URL}`);
  console.log(
    `[experiment] requestCount=${TEST_REQUEST_COUNT}, requestIntervalMs=${REQUEST_INTERVAL_MS}, singleRuns=${SINGLE_RUNS}, defaultMaxProcessNum=${DEFAULT_MAX_PROCESS_NUM}`
  );

  const health = (await request('/health')).data;
  console.log('[experiment] initial health=', JSON.stringify(health, null, 2));

  const bootstrapResult = await bootstrap();
  console.log('[experiment] bootstrap=', JSON.stringify(bootstrapResult, null, 2));

  const single = await measureSingleRequestAverage();
  console.log('[experiment] single average=', JSON.stringify(single, null, 2));

  const interval = await measureIntervalRealtime(single.processingDurationSec.avg);
  console.log('[experiment] interval realtime=', JSON.stringify(interval, null, 2));

  const batch10 = await measureBatchFlush10();
  console.log('[experiment] batch10=', JSON.stringify(batch10, null, 2));

  await configure(DEFAULT_MAX_PROCESS_NUM, 3);

  const summary = {
    startedAt,
    finishedAt: new Date().toISOString(),
    backendUrl: BACKEND_URL,
    testRequestCount: TEST_REQUEST_COUNT,
    requestIntervalMs: REQUEST_INTERVAL_MS,
    single,
    interval,
    batch10,
  };

  console.log('EXPERIMENT_RESULT_JSON_START');
  console.log(JSON.stringify(summary, null, 2));
  console.log('EXPERIMENT_RESULT_JSON_END');

  if (!interval.complete || !batch10.complete || interval.improvedVsSequential === false) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error('[experiment] failed:', error);
  process.exitCode = 1;
});
