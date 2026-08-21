const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
const TOTAL_REQUESTS = Number(process.env.TOTAL_REQUESTS || 10);
const MAX_PROCESS_NUM = Number(process.env.MAX_PROCESS_NUM || 3);
const REQUEST_INTERVAL_MS = Number(process.env.REQUEST_INTERVAL_MS || 200);
const CHAT_PATIENT_SEC = Number(process.env.CHAT_PATIENT_SEC || 3);
const POLL_INTERVAL_MS = Number(process.env.POLL_INTERVAL_MS || 500);
const TIMEOUT_MS = Number(process.env.TIMEOUT_MS || 300000);

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const round = (value, digits = 3) => Number(value.toFixed(digits));

const questions = [
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

function isoToMs(iso) {
  return new Date(iso).getTime();
}

async function drainAnnotations(expectedIds) {
  const expected = new Set(expectedIds);
  const received = new Map();
  for (let i = 0; i < 20 && received.size < expected.size; i += 1) {
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

async function main() {
  const startedAt = new Date().toISOString();
  console.log(`[batch-patient] backend=${BACKEND_URL}`);
  console.log(
    `[batch-patient] totalRequests=${TOTAL_REQUESTS}, maxProcessNum=${MAX_PROCESS_NUM}, requestIntervalMs=${REQUEST_INTERVAL_MS}, chatPatientSec=${CHAT_PATIENT_SEC}`
  );

  await postJson('/test/bootstrap-save-users', { users: ['user1', 'user2'] });
  await postJson('/test/reset-observability', {});
  const config = (await postJson('/test/config', { maxProcessNum: MAX_PROCESS_NUM, chatPatientSec: CHAT_PATIENT_SEC })).data;
  console.log('[batch-patient] config=', JSON.stringify(config, null, 2));

  const experimentId = `batch-patient-${Date.now()}`;
  const sends = [];
  const snapshots = [];
  const firstSendMs = Date.now();

  for (let i = 1; i <= TOTAL_REQUESTS; i += 1) {
    const userId = i % 2 ? 'user1' : 'user2';
    const sessionId = i % 2 ? 'saved-session-user1' : 'saved-session-user2';
    const requestId = `${experimentId}-${i}`;
    const sendStartedMs = Date.now();
    const questionText = questions[(i - 1) % questions.length];
    const body = {
      userId,
      sessionId,
      seq: i,
      text: questionText,
      lang: 'ko-KR',
      requestId,
    };
    const accepted = (await postJson('/text', body)).data;
    const status = (await request('/test/status')).data;
    sends.push({ seq: i, userId, sessionId, requestId, questionText, sendOffsetSec: round((sendStartedMs - firstSendMs) / 1000), accepted });
    snapshots.push({
      event: `after-send-${i}`,
      atOffsetSec: round((Date.now() - firstSendMs) / 1000),
      currentChatInputs: status.currentChatInputs,
      chatProcessQueue: status.chatProcessQueue,
      runningBackgroundBatches: status.runningBackgroundBatches,
      batchCount: status.batches.length,
      latestBatchSize: status.batches.at(-1)?.size ?? null,
    });
    console.log(
      `[send] seq=${i}, flushedNow=${accepted.flushedNow}, current=${status.currentChatInputs}, processQueue=${status.chatProcessQueue}, running=${status.runningBackgroundBatches}`
    );
    if (i < TOTAL_REQUESTS) await sleep(REQUEST_INTERVAL_MS);
  }

  const expectedIds = sends.map((item) => item.requestId);
  const expected = new Set(expectedIds);
  const pollStartedMs = Date.now();
  let finalStatus = null;

  while (Date.now() - pollStartedMs < TIMEOUT_MS) {
    const status = (await request('/test/status')).data;
    finalStatus = status;
    const scoped = status.requestDetails.filter((item) => expected.has(item.requestId));
    const completed = scoped.filter((item) => item.status === 'completed');
    const failed = scoped.filter((item) => item.status === 'failed');
    snapshots.push({
      event: 'poll',
      atOffsetSec: round((Date.now() - firstSendMs) / 1000),
      completed: completed.length,
      failed: failed.length,
      currentChatInputs: status.currentChatInputs,
      chatProcessQueue: status.chatProcessQueue,
      runningBackgroundBatches: status.runningBackgroundBatches,
      batchCount: status.batches.length,
      batchSizes: status.batches.map((batch) => batch.size),
    });
    console.log(
      `[poll] completed=${completed.length}/${TOTAL_REQUESTS}, failed=${failed.length}, current=${status.currentChatInputs}, queue=${status.chatProcessQueue}, running=${status.runningBackgroundBatches}, batches=${status.batches.map((b) => b.size).join('/')}`
    );
    if (completed.length + failed.length >= TOTAL_REQUESTS) break;
    await sleep(POLL_INTERVAL_MS);
  }

  if (!finalStatus) finalStatus = (await request('/test/status')).data;
  const annotations = await drainAnnotations(expectedIds);
  const annotationById = new Map(annotations.map((item) => [item.requestId, item]));
  const sendById = new Map(sends.map((item) => [item.requestId, item]));
  const requestDetails = finalStatus.requestDetails
    .filter((item) => expected.has(item.requestId))
    .sort((a, b) => a.seq - b.seq);
  const batches = finalStatus.batches.filter((batch) => batch.requestIds?.some((id) => expected.has(id)));

  const batchRows = batches.map((batch, index) => {
    const firstAcceptedMs = Math.min(
      ...batch.requestIds.map((id) => {
        const request = requestDetails.find((item) => item.requestId === id);
        return request?.acceptedAt ? request.acceptedAt * 1000 : Infinity;
      })
    );
    const startedMs = isoToMs(batch.startedAt);
    const completedMs = batch.completedAt ? isoToMs(batch.completedAt) : null;
    const seqs = batch.requestIds
      .map((id) => requestDetails.find((item) => item.requestId === id)?.seq)
      .filter(Boolean);
    return {
      batchNo: index + 1,
      batchId: batch.batchId,
      size: batch.size,
      seqs,
      flushReason: batch.size >= MAX_PROCESS_NUM ? 'maxProcessNum 도달 즉시 flush' : 'patient timeout flush',
      firstRequestOffsetSec: round((firstAcceptedMs - firstSendMs) / 1000),
      batchStartedOffsetSec: round((startedMs - firstSendMs) / 1000),
      waitFromFirstRequestSec: round((startedMs - firstAcceptedMs) / 1000),
      durationSec: batch.durationSec,
      completedOffsetSec: completedMs ? round((completedMs - firstSendMs) / 1000) : null,
      status: batch.status,
    };
  });

  const requestRows = requestDetails.map((item) => {
    const batch = batchRows.find((row) => row.seqs.includes(item.seq));
    const annotation = annotationById.get(item.requestId);
    const sent = sendById.get(item.requestId);
    return {
      seq: item.seq,
      requestId: item.requestId,
      batchNo: batch?.batchNo ?? null,
      batchId: batch?.batchId ?? null,
      userId: item.userId,
      questionText: sent?.questionText ?? null,
      acceptedOffsetSec: round((item.acceptedAt * 1000 - firstSendMs) / 1000),
      executionStartOffsetSec: batch?.batchStartedOffsetSec ?? null,
      waitUntilExecutionStartSec: batch ? round(batch.batchStartedOffsetSec - round((item.acceptedAt * 1000 - firstSendMs) / 1000)) : null,
      completedOffsetSec: item.completedAtIso ? round((new Date(item.completedAtIso).getTime() - firstSendMs) / 1000) : null,
      queueWaitSec: item.queueWaitSec,
      processingDurationSec: item.processingDurationSec,
      totalLatencySec: item.totalLatencySec,
      answerState: annotation?.answerState ?? null,
      page: annotation?.page ?? null,
      resultPreview: annotation?.annotation ? String(annotation.annotation).replace(/\s+/g, ' ').slice(0, 220) : null,
      status: item.status,
    };
  });

  const executionGroups = batchRows.map((batch) => ({
    batchNo: batch.batchNo,
    batchId: batch.batchId,
    executionStartOffsetSec: batch.batchStartedOffsetSec,
    completedOffsetSec: batch.completedOffsetSec,
    durationSec: batch.durationSec,
    flushReason: batch.flushReason,
    requestResults: requestRows
      .filter((row) => row.batchNo === batch.batchNo)
      .map((row) => ({
        seq: row.seq,
        userId: row.userId,
        questionText: row.questionText,
        resultPreview: row.resultPreview,
        totalLatencySec: row.totalLatencySec,
      })),
  }));

  const expectedBatchSizes = [3, 3, 3, 1];
  const actualBatchSizes = batchRows.map((batch) => batch.size);
  const sizePatternPass = JSON.stringify(actualBatchSizes) === JSON.stringify(expectedBatchSizes);
  const lastBatch = batchRows.at(-1);
  const lastPatientWaitPass = lastBatch && lastBatch.size === 1 && lastBatch.waitFromFirstRequestSec >= CHAT_PATIENT_SEC;

  const summary = {
    startedAt,
    finishedAt: new Date().toISOString(),
    backendUrl: BACKEND_URL,
    totalRequests: TOTAL_REQUESTS,
    maxProcessNum: MAX_PROCESS_NUM,
    requestIntervalMs: REQUEST_INTERVAL_MS,
    chatPatientSec: CHAT_PATIENT_SEC,
    expectedBatchSizes,
    actualBatchSizes,
    sizePatternPass,
    lastPatientWaitPass,
    verdict:
      sizePatternPass && lastPatientWaitPass
        ? 'PASS: 3/3/3은 maxProcessNum 도달 즉시 flush, 마지막 1개는 patient timeout 후 flush됨'
        : 'FAIL/CHECK: batch size 또는 마지막 patient wait 조건 확인 필요',
    sends,
    snapshots,
    batchRows,
    requestRows,
    executionGroups,
    annotationsCount: annotations.length,
  };

  console.log('BATCH_PATIENT_RESULT_JSON_START');
  console.log(JSON.stringify(summary, null, 2));
  console.log('BATCH_PATIENT_RESULT_JSON_END');

  if (!sizePatternPass || !lastPatientWaitPass) process.exitCode = 1;
}

main().catch((error) => {
  console.error('[batch-patient] failed:', error);
  process.exitCode = 1;
});
