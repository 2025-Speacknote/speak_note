import asyncio
import uuid

from langchain_community.vectorstores import FAISS
from langchain_upstage import UpstageEmbeddings
from typing import Callable, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from collections import defaultdict
from langchain_teddynote import logging

import speak_note.tools.llms as llms
import speak_note.tools.myPDFparser as myPDFparser
import speak_note.tools.en_myPDFparser as en_myPDFparser
from speak_note.work_flows.RAG  import basic_RAG
from speak_note.instance.instance import Instance

'''
### retriever 하이퍼 파라미터
| 설정                                       | 설명                    | 장점                           | 단점                 |
| ---------------------------------------- | --------------------- | ---------------------------- | ------------------ |
| `k=1`                                    | 가장 유사한 문서 1개          | 빠름, 단순                       | 답변이 부실할 수 있음       |
| `k=5`, `mmr`, `lambda_mult=0.25`         | 다양한 문맥 확보, 유사도 적절히 반영 | **유사한 문서 중 다양성 확보**, 정확도+풍부함 | 느릴 수 있음            |
| `fetch_k=50`, `k=5` + `mmr`              | 후보군 확장 → Top 다양성 선택   | 유사한 문서가 많을 때 좋음              | `fetch_k`가 클수록 느려짐 |
| `score_threshold=0.8`                    | 유사도 높은 문서만 사용         | 노이즈 방지, 불필요 문서 제거            | 질의가 불명확하면 빈 결과     |
| `filter={...}`                           | 특정 조건 필터링             | 특정 context 제한 가능             | 일반 RAG엔 부적합        |
| `search_type="similarity"` + `k=5` (기본값) | 단순 유사도 정렬             | 빠르고 안정적                      | 다양성 부족 가능          |

'''

##  실험 적용하며 개선할 하이퍼 파라미터들

### 
retriever_configs = {
    "balanced": {
        "search_type": "mmr",
        "search_kwargs": {"k": 4, "fetch_k": 20, "lambda_mult": 0.3}
    },
    "strict": {
        "search_type": "similarity_score_threshold",
        "search_kwargs": {"k": 5, "score_threshold": 0.8}
    },
    "fast": {
        "search_kwargs": {"k": 2}
    }
}

### 앞으로 계속 수정할 코드.
context_configs = {
    "gpt": {
        "chunk_size": 500,
        "chunk_overlap": 50
    },
    "upstage": {
        "chunk_size": 500,
        "chunk_overlap": 50
    }
}

#  "embeddings": OpenAIEmbeddings(),
#  "embeddings": UpstageEmbeddings(model="solar-embedding-1-large"),


class Context(Instance):
    # 문서 맥락정보 
    # Context생성 -> set_context -> set_retriever 파이프라인으로 작업이 완료된다.
    # Context생성은 한번에 여러 요청이 들어올수있다.
    def __init__(self, document, user_id):
        # self.id = uuid.uuid4() #현재생성시간
        super().__init__()
        self.user_id = user_id
        self.document = document

        # default로 "gpt"기반, "balance"로 생성.
        self.set_context(context_config=context_configs["gpt"], embedding=OpenAIEmbeddings())
        self.set_retriever(retriever_config=retriever_configs["balanced"])
        self.basic_RAG = basic_RAG(self.retriever)

    @classmethod # 인스턴스(self)가 아닌 클래스 자체(cls)를 첫 번째 인자로 받음
    async def create(cls, document_path: str, user_id):  # cls는 일반적으로 "클래스 자신"을 가리키는 변수명
        document = await myPDFparser.upstageParser2Document(file_path=document_path)
        return cls(document, user_id)

    def set_context(self, context_config, embedding):
        self.text_splitter = RecursiveCharacterTextSplitter(**context_config)
        self.split_documents = self.text_splitter.split_documents(self.document)
        self.vectorstore = FAISS.from_documents(documents=self.split_documents, embedding=embedding)

    def set_retriever(self, retriever_config):
        self.retriever = self.vectorstore.as_retriever(**retriever_config)

    def get_retriever(self):
        return self.retriever

    

class en_Context(Context):
    @classmethod
    async def create(cls, document_path: str):
        document = await en_myPDFparser.upstageParser2Document(file_path=document_path)
        return cls(document)
