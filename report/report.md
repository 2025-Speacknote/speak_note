# SpeakNote 큐/코루틴 테스트 실행 보고서

## 0. 바로 실행 스크립트

> 전제: 프로젝트 루트에서 실행한다.  
> 테스트 기준: **10개 요청**, **1초 요청 간격**, **실제 LLM API 사용**.

### 0.1 백엔드 서버 실행

```bash
conda run -n speaknote python server.py
```

서버 확인:

```bash
curl -sS http://127.0.0.1:8000/health | python -m json.tool
```

기대 핵심값:

```json
{
  "ok": true,
  "maxProcessNum": 10,
  "chatPatientSec": 3
}
```

### 0.2 전체 자동 실험 실행

아래 명령 하나로 전부 실행한다.

```bash
npm --prefix speaknote-frontend run experiment
```

자동 실험이 수행하는 단계:

1. `save/user1.json`, `save/user2.json` 기반 Context/Chat 로드
2. **단일 요청 평균 처리시간 측정**
   - `maxProcessNum=1`
   - 단일 요청을 즉시 flush
   - 기본 3회 반복
   - `processingDurationSec.avg` 산출
3. **처리시간 > 요청간격 상황의 실시간성 측정**
   - 요청 수: 10개
   - 요청 간격: 1000ms
   - `maxProcessNum=1`로 각 요청을 도착 즉시 독립 background batch로 dispatch
   - 첫 응답 이후 completion gap이 단일 처리시간이 아니라 요청 간격에 가까운지 측정
4. **10개 batch flush 확인**
   - `maxProcessNum=10`
   - 10개 요청 burst
   - 첫 batch size가 10인지 확인
5. `EXPERIMENT_RESULT_JSON_START` / `EXPERIMENT_RESULT_JSON_END` 사이에 최종 JSON 출력

조건 변경:

```bash
BACKEND_URL=http://127.0.0.1:8000 \
TEST_REQUEST_COUNT=10 \
REQUEST_INTERVAL_MS=1000 \
SINGLE_RUNS=3 \
MAX_PROCESS_NUM=10 \
POLL_INTERVAL_MS=500 \
TIMEOUT_MS=300000 \
npm --prefix speaknote-frontend run experiment
```

### 0.3 프런트 UI 실행

```bash
npm --prefix speaknote-frontend run dev
```

브라우저:

```text
http://localhost:3000
```

---

## 1. 테스트용 API 목록

### `GET /health`

서버와 큐 설정 확인.

```bash
curl -sS http://127.0.0.1:8000/health | python -m json.tool
```

주요 필드:

- `maxProcessNum`: 현재 batch max. 기본 10
- `chatPatientSec`: max에 못 미쳤을 때 강제 flush 대기 시간
- `currentChatInputs`: 아직 batch로 flush되지 않은 입력 수
- `chatProcessQueue`: worker가 아직 가져가지 않은 batch 수
- `runningBackgroundBatches`: 현재 비동기 실행 중인 batch 수
- `batches`: 최근 batch 이벤트
- `requests`: queued/processing/completed/failed 개수

### `POST /test/bootstrap-save-users`

`save/user1.json`, `save/user2.json`을 실제 Context/Chat 객체로 로드한다.

```bash
curl -sS -X POST http://127.0.0.1:8000/test/bootstrap-save-users \
  -H 'Content-Type: application/json' \
  -d '{"users":["user1","user2"],"sessionPrefix":"saved-session"}' | python -m json.tool
```

### `POST /test/config`

테스트 중 queue 설정 변경.

단일/실시간성 테스트용, 요청 즉시 flush:

```bash
curl -sS -X POST http://127.0.0.1:8000/test/config \
  -H 'Content-Type: application/json' \
  -d '{"maxProcessNum":1,"chatPatientSec":30}' | python -m json.tool
```

10개 batch flush 테스트용:

```bash
curl -sS -X POST http://127.0.0.1:8000/test/config \
  -H 'Content-Type: application/json' \
  -d '{"maxProcessNum":10,"chatPatientSec":3}' | python -m json.tool
```

### `POST /text`

텍스트 질의 요청. 실제 LLM API로 처리되는 작업이다.

```bash
curl -sS -X POST http://127.0.0.1:8000/text \
  -H 'Content-Type: application/json' \
  -d '{
    "userId":"user1",
    "sessionId":"saved-session-user1",
    "seq":1,
    "text":"G7 히로시마 AI 프로세스 행동강령은 무엇을 요구했어?",
    "lang":"ko-KR",
    "requestId":"manual-user1-1"
  }' | python -m json.tool
```

### `POST /test/flush-chat-now`

현재 `currentChatInputs`에 쌓인 요청을 즉시 batch로 flush한다. 단일 요청 처리시간 측정에 사용한다.

```bash
curl -sS -X POST http://127.0.0.1:8000/test/flush-chat-now \
  -H 'Content-Type: application/json' \
  -d '{}' | python -m json.tool
```

### `GET /test/status`

request/batch별 처리 상태 확인.

```bash
curl -sS http://127.0.0.1:8000/test/status | python -m json.tool
```

핵심 측정 필드:

- `requestDetails[].queueWaitSec`
- `requestDetails[].processingDurationSec`
- `requestDetails[].totalLatencySec`
- `requestDetails[].completedAtIso`
- `batches[].size`
- `batches[].durationSec`

### `GET /callbacks/annotations`

완료된 annotation 결과 polling. 결과가 없으면 HTTP 204.

```bash
curl -sS http://127.0.0.1:8000/callbacks/annotations | python -m json.tool
```

### `POST /test/reset-observability`

관측 상태와 pending chat queue를 초기화한다. Context/Chat 객체는 유지한다.

```bash
curl -sS -X POST http://127.0.0.1:8000/test/reset-observability \
  -H 'Content-Type: application/json' \
  -d '{}' | python -m json.tool
```

---

## 2. 측정 기준

### 2.1 단일 요청 평균 처리시간

자동 스크립트는 다음 조건으로 측정한다.

- `maxProcessNum=1`
- `chatPatientSec=30`
- 단일 요청 제출
- 즉시 `/test/flush-chat-now`
- 완료될 때까지 `/test/status` polling
- `processingDurationSec` 수집
- 기본 3회 평균 산출

최종 JSON 위치:

```json
{
  "single": {
    "processingDurationSec": {
      "values": [12.1, 11.8, 12.4],
      "avg": 12.1
    }
  }
}
```

### 2.2 처리시간 > 요청간격일 때 실시간 반환 여부

목표 예시:

```text
좋은 예:
12초 -> 1번째 반환
13초 -> 2번째 반환
14초 -> 3번째 반환
...

나쁜 예:
12초 -> 1번째 반환
24초 -> 2번째 반환
36초 -> 3번째 반환
...
```

자동 스크립트 조건:

- 요청 수: 10개
- 요청 간격: 1000ms
- `maxProcessNum=1`
- 각 요청은 들어오자마자 독립 background batch로 dispatch
- `completedAtIso` 기준 completion gap 계산

판정 필드:

```json
{
  "interval": {
    "requestCount": 10,
    "requestIntervalMs": 1000,
    "singleAverageProcessingSec": 12.1,
    "firstCompletionOffsetSec": 12.3,
    "completionGapsSec": [1.0, 1.2, 0.9, 1.1],
    "avgCompletionGapSec": 1.05,
    "improvedVsSequential": true,
    "followsRequestInterval": true,
    "verdict": "PASS: 첫 응답 이후 반환 간격이 단일 처리시간보다 훨씬 짧고 요청 간격에 근접함"
  }
}
```

### 2.3 10개 batch flush 확인

자동 스크립트 조건:

- `maxProcessNum=10`
- 10개 요청 burst
- batch 이벤트에서 `size: 10` 확인

최종 JSON 위치:

```json
{
  "batch10": {
    "maxProcessNum": 10,
    "requestCount": 10,
    "batches": [
      { "size": 10, "durationSec": 12.7 }
    ]
  }
}
```

---

## 3. 수동 실시간성 테스트 스크립트

아래는 자동 스크립트를 쓰지 않고 curl로 직접 10개 요청을 1초 간격으로 넣는 예시다.

```bash
# 1) 유저 로드
curl -sS -X POST http://127.0.0.1:8000/test/bootstrap-save-users \
  -H 'Content-Type: application/json' \
  -d '{"users":["user1","user2"]}' | python -m json.tool

# 2) 상태/queue 초기화
curl -sS -X POST http://127.0.0.1:8000/test/reset-observability \
  -H 'Content-Type: application/json' \
  -d '{}' >/dev/null

# 3) 요청 즉시 독립 dispatch되도록 설정
curl -sS -X POST http://127.0.0.1:8000/test/config \
  -H 'Content-Type: application/json' \
  -d '{"maxProcessNum":1,"chatPatientSec":30}' | python -m json.tool

# 4) 10개 요청을 1초 간격으로 전송
for i in 1 2 3 4 5 6 7 8 9 10; do
  curl -sS -X POST http://127.0.0.1:8000/text \
    -H 'Content-Type: application/json' \
    -d "{\"userId\":\"user1\",\"sessionId\":\"saved-session-user1\",\"seq\":$i,\"text\":\"G7 히로시마 AI 프로세스 행동강령을 요약해줘.\",\"lang\":\"ko-KR\",\"requestId\":\"interval-user1-$i\"}" | python -m json.tool
  sleep 1
done

# 5) completion 시간 확인
curl -sS http://127.0.0.1:8000/test/status | python -m json.tool
```

---

## 4. 구현 변경 요약

### `server.py`

- 기본 `maxProcessNum`을 10으로 설정
  - `MAX_PROCESS_NUM` 환경변수로 override 가능
- `/test/config` 추가
  - 테스트 중 `maxProcessNum`, `chatPatientSec` 변경 가능
- `/test/flush-chat-now` 추가
  - 단일 요청 처리시간 측정용 즉시 flush
- `/test/reset-observability` 보강
  - request/batch 관측 상태와 pending chat queue 초기화
- request별 `processingDurationSec`, `completedAtIso` 기록 추가
- `speak_note/` 내부 파일은 수정하지 않음

### `speaknote-frontend/scripts/run-experiment.mjs`

- 기본 테스트 요청 수를 10개로 변경
- 단일 요청 평균 처리시간 측정 추가
- 1초 간격 10개 요청의 completion gap 측정 추가
- 10개 batch flush 확인 추가

### `speaknote-frontend/app/page.js`

- UI 기본 요청 수를 10개로 변경
- CLI 자동 실험이 단일 평균/1초 간격 반환 개선 여부를 측정한다는 설명 추가

---

## 5. 검증

### 문법 검증

```bash
python -m py_compile server.py
node --check speaknote-frontend/scripts/run-experiment.mjs
```

결과: 통과

### 프런트 빌드 검증

```bash
npm --prefix speaknote-frontend run build
```

결과: 통과

```text
✓ Compiled successfully
✓ Generating static pages (5/5)
```

---

## 6. 최종 실행 명령 재정리

가장 중요한 실행 명령은 아래 2개다.

```bash
conda run -n speaknote python server.py
```

다른 터미널에서:

```bash
TEST_REQUEST_COUNT=10 REQUEST_INTERVAL_MS=1000 SINGLE_RUNS=3 MAX_PROCESS_NUM=10 \
npm --prefix speaknote-frontend run experiment
```


---

## 7. 실제 LLM API 실행 결과 정리

실행 명령:

```bash
TEST_REQUEST_COUNT=10 REQUEST_INTERVAL_MS=1000 SINGLE_RUNS=3 MAX_PROCESS_NUM=10 \
POLL_INTERVAL_MS=500 TIMEOUT_MS=300000 \
npm --prefix speaknote-frontend run experiment
```

실행 시각: 2026-08-20 17:19~17:20 KST

테스트는 fallback/smoketest가 아니라 `save/user1.json`, `save/user2.json` 기반 Context/Chat을 로드한 뒤 실제 LLM API 호출로 수행했다.

### 7.1 단일 요청 평균 처리시간

조건:

- `maxProcessNum=1`
- 단일 요청 제출
- 즉시 flush
- 3회 반복

결과:

```json
{
  "processingDurationSec": {
    "values": [8.404, 10.267, 13.043],
    "avg": 10.571,
    "min": 8.404,
    "max": 13.043,
    "p50": 10.267,
    "p90": 13.043
  },
  "totalLatencySec": {
    "values": [8.657, 10.378, 13.531],
    "avg": 10.855
  }
}
```

정리:

- 실제 LLM 단일 처리 평균: **10.571초**
- request accept부터 완료까지의 평균 total latency: **10.855초**
- 이후 before/after 비교의 기준 처리시간은 **10.571초/request**로 둔다.

### 7.2 1초 간격 10개 요청의 실제 반환 결과

조건:

- 요청 수: 10개
- 요청 간격: 1초
- 단일 평균 처리시간: 10.571초
- 각 요청은 `maxProcessNum=1`로 들어오는 즉시 독립 background batch 처리
- 목적: 처리시간이 요청간격보다 훨씬 길어도, 첫 응답 이후 반환이 10초 단위로 밀리지 않고 요청 흐름에 가깝게 나오는지 확인

seq별 완료 offset:

```json
[
  { "seq": 1, "acceptedOffsetSec": 0.000, "completedOffsetSec": 9.379, "totalLatencySec": 9.378 },
  { "seq": 2, "acceptedOffsetSec": 1.002, "completedOffsetSec": 12.227, "totalLatencySec": 11.224 },
  { "seq": 3, "acceptedOffsetSec": 2.005, "completedOffsetSec": 11.385, "totalLatencySec": 9.376 },
  { "seq": 4, "acceptedOffsetSec": 3.011, "completedOffsetSec": 14.315, "totalLatencySec": 11.300 },
  { "seq": 5, "acceptedOffsetSec": 4.018, "completedOffsetSec": 13.364, "totalLatencySec": 9.341 },
  { "seq": 6, "acceptedOffsetSec": 5.026, "completedOffsetSec": 13.633, "totalLatencySec": 8.605 },
  { "seq": 7, "acceptedOffsetSec": 6.031, "completedOffsetSec": 16.701, "totalLatencySec": 10.666 },
  { "seq": 8, "acceptedOffsetSec": 7.039, "completedOffsetSec": 16.650, "totalLatencySec": 9.609 },
  { "seq": 9, "acceptedOffsetSec": 8.043, "completedOffsetSec": 16.793, "totalLatencySec": 8.748 },
  { "seq": 10, "acceptedOffsetSec": 9.046, "completedOffsetSec": 17.706, "totalLatencySec": 8.657 }
]
```

실제 completion event 시간순:

```json
[
  { "seq": 1, "completedOffsetSec": 9.379 },
  { "seq": 3, "completedOffsetSec": 11.385 },
  { "seq": 2, "completedOffsetSec": 12.227 },
  { "seq": 5, "completedOffsetSec": 13.364 },
  { "seq": 6, "completedOffsetSec": 13.633 },
  { "seq": 4, "completedOffsetSec": 14.315 },
  { "seq": 8, "completedOffsetSec": 16.650 },
  { "seq": 7, "completedOffsetSec": 16.701 },
  { "seq": 9, "completedOffsetSec": 16.793 },
  { "seq": 10, "completedOffsetSec": 17.706 }
]
```

완료시간순 gap:

```json
[2.006, 0.842, 1.137, 0.269, 0.682, 2.335, 0.051, 0.092, 0.913]
```

요약:

```json
{
  "firstCompletionOffsetSec": 9.379,
  "lastCompletionOffsetSec": 17.706,
  "avgCompletionGapSec": 0.925,
  "maxCompletionGapSec": 2.335,
  "singleAverageProcessingSec": 10.571,
  "improvedVsSequential": true,
  "followsRequestInterval": true
}
```

판정:

- 첫 응답은 **9.379초** 후 반환됐다.
- 이후 완료 이벤트 평균 gap은 **0.925초**로, 요청 간격 1초에 근접했다.
- 완료 순서는 일부 out-of-order였다. 예: `seq=3`이 `seq=2`보다 먼저 완료.
- 하지만 목표는 순서 보장이 아니라 “10초 처리시간 때문에 응답이 10초 단위로 밀리는지 여부”였고, 실제로는 밀리지 않았다.
- 실시간성 개선: **PASS**

---

## 8. Before / After 비교

### 8.1 비교 기준

실제 측정된 단일 평균 처리시간:

```text
T = 10.571초/request
```

요청 조건:

```text
N = 10개 요청
요청 간격 = 1초
마지막 요청 도착 시점 ≈ 9초
```

### 8.2 Before: 비동기 코루틴 처리가 없고 순차 처리였다면

가정:

- 서버가 한 번에 하나의 LLM 요청만 처리한다.
- 앞 요청이 끝나야 다음 요청 처리를 시작한다.
- 각 요청 처리시간은 평균 10.571초다.
- 요청은 1초마다 들어오지만, 처리 큐에서 순차 대기한다.

예상 완료 시각:

```text
1번째 완료 ≈ 10.571초
2번째 완료 ≈ 21.142초
3번째 완료 ≈ 31.713초
4번째 완료 ≈ 42.284초
5번째 완료 ≈ 52.855초
6번째 완료 ≈ 63.426초
7번째 완료 ≈ 73.997초
8번째 완료 ≈ 84.568초
9번째 완료 ≈ 95.139초
10번째 완료 ≈ 105.710초
```

즉 사용자가 말한 나쁜 예시와 같은 형태가 된다.

```text
약 10.6초 -> 1번째
약 21.1초 -> 2번째
약 31.7초 -> 3번째
...
약 105.7초 -> 10번째
```

순차 처리 예상치:

```json
{
  "expectedSequentialLastCompletionSec": 105.710,
  "expectedSequentialAverageCompletionOffsetSec": 58.141,
  "expectedSequentialAverageUserLatencySec": 53.641
}
```

설명:

- 평균 completion offset = `(10.571 * (1+...+10)) / 10 = 58.141초`
- 평균 사용자 latency는 요청이 1초마다 들어온 점을 빼서 약 `53.641초`
- 10번째 요청은 9초에 들어왔지만 105.710초에 끝나므로 10번째 사용자 latency는 약 `96.710초`

### 8.3 After: 현재 비동기 코루틴/background batch 처리 결과

실제 완료 시각:

```text
첫 완료: 9.379초
마지막 완료: 17.706초
첫 완료 이후 평균 반환 gap: 0.925초
```

실제 평균 completion offset:

```text
(9.379 + 12.227 + 11.385 + 14.315 + 13.364 + 13.633 + 16.701 + 16.650 + 16.793 + 17.706) / 10
= 14.215초
```

실제 평균 사용자 latency:

```text
(9.378 + 11.224 + 9.376 + 11.300 + 9.341 + 8.605 + 10.666 + 9.609 + 8.748 + 8.657) / 10
= 9.690초
```

실제 결과:

```json
{
  "actualFirstCompletionSec": 9.379,
  "actualLastCompletionSec": 17.706,
  "actualAverageCompletionOffsetSec": 14.215,
  "actualAverageUserLatencySec": 9.690,
  "actualAverageCompletionGapSec": 0.925
}
```

### 8.4 개선 폭

```json
{
  "lastCompletionSpeedup": "105.710 / 17.706 = 5.97x faster",
  "averageCompletionOffsetSpeedup": "58.141 / 14.215 = 4.09x faster",
  "averageUserLatencySpeedup": "53.641 / 9.690 = 5.54x faster"
}
```

표로 정리:

| 항목 | Before: 순차 처리 예상 | After: 실제 비동기 처리 | 개선 |
| --- | ---: | ---: | ---: |
| 첫 응답 | 10.571초 | 9.379초 | 약 1.13배 빠름 |
| 마지막 응답 | 105.710초 | 17.706초 | 약 5.97배 빠름 |
| 평균 completion offset | 58.141초 | 14.215초 | 약 4.09배 빠름 |
| 평균 사용자 latency | 53.641초 | 9.690초 | 약 5.54배 빠름 |
| 첫 응답 이후 반환 간격 | 약 10.571초 | 평균 0.925초 | 요청 간격 1초에 근접 |

### 8.5 결론

비동기 코루틴/background batch 처리가 없었다면 10개 요청 완료까지 약 **105.710초**가 걸렸을 것으로 예상된다.

현재 구현에서는 실제 LLM API 처리 기준으로 10개 요청이 **17.706초** 내 모두 완료됐다.

핵심적으로, 단일 요청 처리시간이 약 **10.571초**인데도 첫 응답 이후 결과 반환 gap은 평균 **0.925초**였다. 따라서 요청이 1초 간격으로 들어오는 상황에서 순차 처리처럼 `10초 → 20초 → 30초`로 밀리지 않고, `첫 응답 이후 1초 내외`로 반환되는 개선을 확인했다.

---

## 9. 10개 batch flush 결과

조건:

- `maxProcessNum=10`
- 10개 요청 burst
- user1/user2 교차 요청

결과:

```json
{
  "batchId": "batch-1-58dc4045",
  "size": 10,
  "startedAt": "2026-08-20T17:20:15.188",
  "completedAt": "2026-08-20T17:20:26.646",
  "durationSec": 11.458,
  "completedCount": 10
}
```

판정:

- 첫 batch size가 **10**으로 기록됐다.
- `MAX_PROCESS_NUM=10` 도달 flush가 정상 동작했다.
- batch 내부 10개 요청은 하나의 background batch에서 `asyncio.gather`로 처리되어 batch duration **11.458초**에 완료됐다.

---

## 10. 최종 결론

1. 테스트 요청 수를 10개로 늘렸다.
2. 단일 요청 평균 처리시간은 **10.571초**였다.
3. 1초 간격 10개 요청의 실제 마지막 완료는 **17.706초**였다.
4. 순차 처리였다면 마지막 완료는 약 **105.710초**로 예상된다.
5. 첫 응답 이후 평균 반환 gap은 **0.925초**로, 요청 간격 1초에 근접했다.
6. `MAX_PROCESS_NUM=10` batch flush도 정상 확인했다.
7. 실제 LLM API 기반 테스트 기준으로 비동기 코루틴/background batch 처리 개선 효과를 확인했다.
