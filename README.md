# 🎓 Speak Note: 실시간 강의 AI 주석 시스템  

  &nbsp;

📚 목차  

> - [📌 개요](#-개요)  
> - [🎯 문제 정의 및 기대 효과](#-문제-정의-및-기대-효과)  
> - [✅ Upstage API 활용](#-upstage-api-활용)  
> - [🚀 주요 기능](#-주요-기능)  
> - [🖼️ 데모](#️-데모)  
> - [🔬 기술 구현 요약](#-기술-구현-요약)  
> - [🧰 기술 스택 및 시스템 아키텍처](#-기술-스택-및-시스템-아키텍처)  
> - [🔧 설치 및 사용 방법](#-설치-및-사용-방법)  
> - [📁 프로젝트 구조](#-프로젝트-구조)  
> - [🧑‍🤝‍🧑 팀원 소개](#-팀원-소개)  
> - [💡 참고 자료 및 아이디어 출처](#-참고-자료-및-아이디어-출처)

  &nbsp;

## 📌 개요  
Speak Note는 강의 및 발표 중 실시간으로 음성을 텍스트로 변환하고,
이를 AI가 정제·요약하여 자동으로 슬라이드 및 강의 내용에 맞는 주석을 달아주는 시스템입니다.
학습대상 및 청중에게 발표 내용 이해도 향상과 필기 부담 해소를 목표로 합니다.

  &nbsp;

## 🎯 문제 정의 및 기대 효과  
기존의 STT(Speech-To-Text) 시스템은 보통 음성 녹음이 끝난 뒤 텍스트로 변환하거나 요약하는 데 그쳐, 수업 중에는 여전히 사용자가 수동으로 노트를 작성해야 하는 한계가 있습니다.  

이로 인해 학생들은 수업 시간 동안 발표자의 발언을 받아 적느라 강의 내용을 깊이 있게 이해하기 어려우며, 결국 수업 이후에 별도로 복습해야 수업 내용을 따라갈 수 있는 구조가 형성됩니다.  
이러한 이중 부담은 학습 효율을 떨어뜨릴 뿐 아니라, 경우에 따라 복습 시간이 수업 시간보다 더 오래 걸리는 문제를 초래하기도 합니다.  

**Speak Note는 수업 내용을 실시간으로 정리하고, 해당 내용을 슬라이드에 자동으로 주석으로 연결함으로써 발표자의 발언에 집중할 수 있는 환경을 제공합니다.**  
이를 통해 사용자는 수업 시간 내에 핵심 내용을 충분히 이해할 수 있으며, 수업 후 별도의 복습 없이도 높은 학습 효율을 기대할 수 있습니다.  
  
  &nbsp;

### 🎯 기존 어플리케이션의 한계 정의  
1. **음성인식 모델의 반환 텍스트 품질 한계**
   - 음성인식 텍스트 자체가 어순이나 문법 등이 어긋난 문장을 반환
   - 문맥을 고려하지 못한 채 텍스트를 단순 생성  

2. **사용자와 음성인식 텍스트의 실시간 상호작용 부족**  
   - 실시간으로 원하는 위치에 텍스트를 배치하기 어려움  
   
    &nbsp;

### 🎯 Speak Note 웹의 장점  
1. **Upstage Document Parser + Solar-pro 기반 풍부한 문맥 표현력**  
     - Upstage Document Parser API를 통해 text뿐만 아니라 chart, figure, 수식 등의 정보까지 파악
    
2. **차트나 수식을 자연어로 변환하여 임베딩 가능**  
     - 도표나 수식은 벡터화가 어렵기에 자체 핸들러 함수에서 LLM을 통해 자연어로 변환 후 문맥으로 활용  

3. **자체 CRAG 프로세스를 통한 응답 품질 강화**  
     - RAG 프로세스를 통해 문맥을 고려한 고품질 답변 생성
     - 음성 인식 텍스트가 제공된 PDF문맥에서 벗어나도, 자체 CRAG 프로세스체인을 통해서 PDF와 텍스간의 문맥 유효성 평가
     - 문맥 유효성이 떨어질경우 웹 서치 자료를 기반으로 사용자에게 응답을 제공

4. **드래그앤드롭 기반 직관적인 사용자 인터페이스**  
     - 오른쪽 보드에 텍스트 블럭이 생성되고, 사용자가 이를 원하는 위치에 Drag-Drop 할 수 있음
     - 사용자는 텍스트블럭의 내용을 삭제, 수정을 자유롭게 할 수 있음
  
  &nbsp;

## ✅ Upstage API 활용  

### 1️⃣ RAG 프로세스란?  
단순 질문이 아니라, 질문의 "문맥"을 함께 제공함으로써 AI의 환각(hallucination)을 줄이고 응답 품질을 높이는 기법  
  

![rag-1](https://github.com/user-attachments/assets/2cef23ff-f12d-451f-b245-7eddf9143c72)  
![rag-2](https://github.com/user-attachments/assets/8466d2b4-6911-470b-8986-8eae86c7f30b)  
  
  &nbsp;

### 2️⃣ 문서 내용 추출을 위한 Upstage API 활용  
기존 문서 파서들은 PDF의 텍스트만 처리할 수 있는 한계가 있습니다.  
하지만 **Upstage Document Parser는 텍스트뿐만 아니라 차트, 수식 등도 함께 추출 가능**합니다.  

단, 임베딩 벡터에서 질문에 대해 코사인 유사도를 추출하기 위해서는 차트나 수식을 그대로 임베딩할 수 없기 때문에, 시퀀셜한 자연어로 변환하는 핸들러를 "chart", "figure", "equation" 각 카테고리에 대해 Solar 모델 기반으로 구현했습니다.  

<img width="944" alt="chart handler 예시" src="https://github.com/user-attachments/assets/5699f70a-0da4-4a9e-a2fd-5040081bdcb0" />  

> Document Parser + Solar LLM으로 PDF의 모든 정보를 시퀀스 텍스트로 정제

  &nbsp;

<img width="923" alt="doc parse process" src="https://github.com/user-attachments/assets/c6560dc5-4a13-42f1-b1bb-1f584bb2d69a" />  

> 전체적인 PDF의 데이터를 추출해오는 프로세스 과정 예시
  &nbsp;

<img width="781" alt="스크린샷 2025-05-28 오전 7 52 57" src="https://github.com/user-attachments/assets/367b711c-1e68-416e-9e37-cce91a2e2d14" />

> 예시 응답과정1. PDF에 있는 내용에 대한 음성 텍스트 처리

  &nbsp;
<img width="781" alt="스크린샷 2025-05-28 오전 7 50 56" src="https://github.com/user-attachments/assets/df118ae5-fa33-4bf0-878d-3569c754903b" />  
> 예시 응답과정2. 문서 내용과 음성텍스트의 문맥이 적합하지 않을때

  &nbsp;

<img width="923" alt="context로 변환" src="https://github.com/user-attachments/assets/468a1534-7a48-4eee-83d9-06583ac15540" />  

  &nbsp;

Document Parser와 Solar-pro LLM 모델의 조합만으로는, PDF의 내용과 직접 관련이 없는 질의가 들어왔을 때  
오히려 제공된 context가 응답 품질을 저하시킨다는 한계가 있었습니다.  
이에 따라 우리 웹사이트는 사용자에게 항상 최적의 응답을 제공하기 위해, 보다 강건한 텍스트 정제 처리를 수행할 수 있는 **CRAG 프로세스**를 도입하였습니다.

  &nbsp;

### 3️⃣ CRAG: Corrective RAG  
CRAG는 검색된 문서들에 대한 자기 반성(self-reflection) 및 자기 평가(self-evaluation) 단계를 포함하여, 검색-생성 파이프라인을 정교하게 다루는 접근법.

<img width="1039" alt="스크린샷 2025-05-28 오전 1 43 09" src="https://github.com/user-attachments/assets/c07a691b-e0f1-408d-b330-0b26d280f799" />

> CRAG 개요도

  &nbsp;

1. **retrieve**
   - 사용자의 질의와, 현재 pdf 강의자료간의 연관성을 계산 및 저장한다.
2. **grade_documents**
   - llm 기반으로 현재 pdf 강의자료와 질의간의 연관성을 평가한다.
3. **query_rewrite**
   - 강의자료와, 질의의 연관성이 떨어질경우 응답을 향상시키기 위해 미리 정해둔 프롬포트와 llm을이용해서 질의의 형식을 향상시킨다.
4. **web_search_node**
   - lm기반으로 향상된 질의에 대한 웹검색 결과를 반환하고 이를 context로 저장한다. 그 후 원본 진의와 해당 context를 다시 RAG chain에 넣음으로써 사용자에게 예외의 상황에도 질높게 가공된 텍스트를 제공한다.
5. **generate**
   - 질의와 강의자료간의 문맥 연관성이 유효하다 판단하면, 그를 이용한 RAG프로세스 결과를 곧바로 제공한다.
  
  &nbsp;

**대부분의 LLM 처리에는 Solar-pro 사용**  
- 쿼리 재작성 및 웹탐색 기반 노드를 제외한 모든 llm은 solar-pro api를 사용해서 처리했다. 웹 탐색 기반 노드에서도 solar-pro를 적용 시켜봤으나, GPT-4o의 답변과 비교했을때, 조금더 정확한 정보를 제공해주는 GPT-4o모델을 채택했다.

  &nbsp;

**웹 탐색 단계만 GPT-4o로 처리해 정보 정확성 확보**  
- 이런 CRAG 자체 프로세스의 도입을 통해서 강의자료의 내용에만 국한되지 않고 사용자에게 항상 향상된 품질의 응답을 제공함으로써, 사용자는 발표자의 발표내용을 요약, 정리한 텍스트를 받아서 사용할수 있다.

  &nbsp;

## 🚀 주요 기능
- 실시간 음성 인식
- 텍스트 정제 및 요약
- 슬라이드 문맥 연동 주석 생성
- 문맥 유효성 검증 (CRAG)
- AI 기반 웹 보강 응답
- 주석 드래그 앤 드롭
- 주석 수정 및 삭제
- 최종 강의 노트 저장
  
  &nbsp;


## 🖼️ 데모  

![주석 편집 및 다운로드](https://github.com/user-attachments/assets/b47d76b8-6f9b-4245-b421-3372b0cc4f60)
> 주석 편집 및 다운로드

&nbsp;

## 🔬 기술 구현 요약  
| 구분     | 구현 방식                                                                 |
| ------ | --------------------------------------------------------------------- |
| 음성 인식  | Google STT API (Streaming Mode) + WebSocket                           |
| 텍스트 정제 | Solar-pro 기반 LLM 처리                                                   |
| 문서 분석  | Upstage Document Parser API + 자체 handler (chart, figure, equation 대응) |
| 문맥 보강  | 자체 CRAG 프로세스 (문맥 평가, 질의 재작성, GPT-4o 검색 포함)                            |
| 통신 방식  | 프론트–백엔드: REST / WebSocket<br>백엔드–AI 서버: HTTP 요청                       |
| 주석 시스템 | Next.js 기반 컴포넌트 인터랙션 + React-dnd 방식 드래그 앤 드롭                          |
| 렌더링 뷰어 | React + react-pdf 기반 슬라이드 렌더링 및 위치 매핑 구현                              | 

  &nbsp;

## 🧰 기술 스택 및 시스템 아키텍처  

- **Frontend**: Next.js, React, TypeScript, Tailwind CSS, react-pdf, react-rnd
- **Backend**: Spring Boot, WebSocket, REST API
- **AI Server**: Flask, Python
- **AI/LLM**: Upstage Document Parser, Solar-pro, GPT-4o
- **STT**: Google STT API

  &nbsp;

## 🔧 설치 및 사용 방법  

```bash
git clone https://github.com/qlqlrh/DAIC-AllYouNeedsToDoOpenYourEyes.git
cd DAIC-AllYouNeedsToDoOpenYourEyes/front

# 의존성 설치
npm install --legacy-peer-deps

# 개발 서버 실행
npm run dev
```
  
  &nbsp;
  
```bash
# 파이썬 ai처리 백앤드 서버 구동

# conda 가상환경 실행
conda init

conda create --name speak_note python=3.11.9

conda activate speak_note

# RAG_LangChain로 이동
cd DAIC-AllYouNeedsToDoOpenYourEyes/RAG_LangChain

# 의존성 설치
pip install -r requirements.txt

# ai 백앤드 서버 구동
python server.py
```
  
  &nbsp;
## 📁 프로젝트 구조
```
.
├── backend
│   ├── src/main/java/org/example/speaknotebackend
│   │   ├── controller
│   │   │   ├── AnnotationController.java           # 주석 조회 및 저장 API
│   │   │   └── PdfController.java                  # PDF 업로드 및 다운로드 API
│   │   ├── service
│   │   │   ├── AnnotationService.java              # 주석 데이터 처리
│   │   │   ├── GoogleSpeechService.java            # Google STT 기반 음성 텍스트 변환
│   │   │   └── PdfService.java                     # 파일 기반 로직 처리
│   │   └── websocket
│   │       └── AudioWebSocketHandler.java          # 음성 및 주석 전달 WebSocket 핸들러
├── front
│   ├── src
│   │   ├── components
│   │   │   ├── AnnotationContext.tsx               # 주석 상태(추가/편집/초기화) 관리
│   │   │   ├── AnnotationPanel.tsx                 # 주석 편의 기능(편집/삭제/드래그) 관리
│   │   │   ├── PDFViewer.tsx                       # PDF 랜더링 및 주석 배치
│   │   │   └── STTRecorder.tsx                     # 음성 녹음 및 전송 WebSocket
│   │   │
├── RAG_LangChain
│   ├── server.py                                   # 텍스트 프런트로 반환 CRAG를 통한 질의 평가-생성 chain 구현
│   ├── myPDFparser.py                              # Upstage DP와 solar 기반 내용 추출 및 임베딩 벡터 생성
│   ├── myUpstageRAG.py                             # 문서 임베딩 벡터와 RAG chain 내장 형태의 myRAG 생성
│   └── prompt.py                                   # llm에 필요한 각 promt 정의 모음

```

  &nbsp;

## 🧑‍🤝‍🧑 팀원 소개
| 이름  | 역할                              | GitHub                                     |
|-----|---------------------------------|--------------------------------------------|
| 김예슬 | PDF 기능, 주석 드래그앤드롭 기능       | [@yeseul](https://github.com/yeseul-kim01) |
| 김동인 | 프론트-백엔드 웹소켓 연동, 실시간 음성인식 기능     | [@qlqlrh](https://github.com/qlqlrh)       |
| 정유성 | RAG 적용, Upstage DP 적용, Solar 적용 | [@yoosung](https://github.com/yoosung5480)       |
  
  &nbsp;

## 💡 참고 자료 및 아이디어 출처

* [Upstage Document Parse](https://www.upstage.ai/products/document-parse)
* [Upstage Building end-to-end RAG system using Solar LLM and MongoDB Atlas](https://www.upstage.ai/blog/en/building-rag-system-using-solar-llm-and-mongodb-atlas)
* https://upstage-ai-education.gitbook.io/upstage-edustage/basics/editor

