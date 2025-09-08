from langchain_core.runnables import Runnable
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from openai import OpenAI
from langchain_upstage import ChatUpstage
from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import UpstageEmbeddings
from langchain_community.vectorstores import DocArrayInMemorySearch
import os
import requests
from bs4 import BeautifulSoup
from openai import OpenAI # openai==1.52.2
from typing import Callable, Dict
from langchain.prompts import PromptTemplate
from collections import defaultdict
from langchain_teddynote import logging
from dotenv import load_dotenv

import speak_note.prompts.english_prompt as en_prompt
import speak_note.prompts.prompt as  prompt


from typing import Any
from abc import ABC, abstractmethod

class RAGChain(ABC):
    @abstractmethod
    def RAG_invoke(self, user_id: str, msg: str, docs: list[Any]) -> str:
        ...
        
    @abstractmethod
    def invoke(self, user_id: str, msg: str) -> str:
        ...

    @abstractmethod
    async def RAG_ainvoke(self, user_id: str, msg: str, llm, docs=None) -> str:
        ...
    
    @abstractmethod
    async def ainvoke(self, user_id: str, msg: str, llm, docs=None) -> str:
        ...


''' 
**모델 스펙**

- 링크: https://platform.openai.com/docs/models

| Model               | Input (1M) | Cached Input (1M) | Output (1M) | Context Window | Max Output Tokens | Knowledge Cutoff |
|---------------------|------------|-------------------|-------------|----------------|-------------------|------------------|
| gpt-4.1             | $2.00      | $0.50             | $8.00       | 1,047,576      | 32,768            | Jun 01, 2024     |
| gpt-4.1-mini        | $0.40      | $0.10             | $1.60       | 1,047,576      | 32,768            | Jun 01, 2024     |
| gpt-4.1-nano        | $0.10      | $0.025            | $0.40       | 1,047,576      | 32,768            | Jun 01, 2024     |
| gpt-4o              | $2.50      | $1.25             | $10.00      | 128,000        | 16,384            | Oct 01, 2023     |
| gpt-4o-mini         | $0.15      | $0.075            | $0.60       | 128,000        | 16,384            | Oct 01, 2023     |
| o1                  | $15.00     | $7.50             | $60.00      | 128,000        | 65,536            | Oct 01, 2023     |
| o1-mini             | $1.10      | $0.55             | $4.40       | 128,000        | 65,536            | Oct 01, 2023     |
| o1-pro              | $150.00    | –                 | $600.00     | 128,000        | 65,536            | Oct 01, 2023     |
| o3-mini             | $1.10      | $0.55             | $4.40       | 200,000        | 100,000           | Oct 01, 2023     |
| gpt-4.5-preview     | $75.00     | $37.50            | $150.00     | –              | –                 | –                |

'''

class basic_RAG(RAGChain):
    def __init__(self, retriever: FAISS):
        self.retriever = retriever
        RAG_prompt_template =  prompt.prompt_to_refine_text      # 사전 정의된 RAG 용 템플릿
        basic_prompt_template = prompt.prompt_basic     # 사전 정의된 basic 템플릿
        self.RAG_prompt_template = PromptTemplate.from_template(RAG_prompt_template)
        self.basic_prompt_template = PromptTemplate.from_template(basic_prompt_template)

    def RAG_invoke(self, msg: str, llm, docs=None) -> str:
        self.RAGchain = (
            {"context": self.retriever, "question": lambda x: x}
            | self.RAG_prompt_template
            | llm
            | StrOutputParser()
        )
        return self.RAGchain.invoke(msg)

    def invoke(self, msg: str, llm) -> str:
        self.basic_chain = (
            self.basic_prompt_template
            | llm
            | StrOutputParser()
        )
        return self.basic_chain.invoke(msg)

    async def RAG_ainvoke(self, msg: str, llm, docs=None) -> str:
        chain = (
            {"context": self.retriever, "question": lambda x: x}
            | self.RAG_prompt_template
            | llm
            | StrOutputParser()
        )
        return await chain.ainvoke(msg)

    async def ainvoke(self, msg: str, llm) -> str:
        chain = (
            self.basic_prompt_template
            | llm
            | StrOutputParser()
        )
        return await chain.ainvoke(msg)
    


class en_RAG(RAGChain):
    def __init__(self, retriever: FAISS):
        self.retriever = retriever
        RAG_prompt_template =  en_prompt.prompt_to_refine_text      # 사전 정의된 RAG 용 템플릿
        basic_prompt_template = en_prompt.prompt_basic     # 사전 정의된 basic 템플릿
        self.RAG_prompt_template = PromptTemplate.from_template(RAG_prompt_template)
        self.basic_prompt_template = PromptTemplate.from_template(basic_prompt_template)
        
    def RAG_invoke(self, msg: str, llm, docs=None) -> str:
        self.RAGchain = (
            {"context": self.retriever, "question": lambda x: x}
            | self.RAG_prompt_template
            | llm
            | StrOutputParser()
        )
        return self.RAGchain.invoke(msg)

    def invoke(self, msg: str, llm) -> str:
        self.basic_chain = (
            self.basic_prompt_template
            | llm
            | StrOutputParser()
        )
        return self.basic_chain.invoke(msg)

    async def RAG_ainvoke(self, msg: str, llm, docs=None) -> str:
        chain = (
            {"context": self.retriever, "question": lambda x: x}
            | self.RAG_prompt_template
            | llm
            | StrOutputParser()
        )
        return await chain.ainvoke(msg)

    async def ainvoke(self, msg: str, llm) -> str:
        chain = (
            self.basic_prompt_template
            | llm
            | StrOutputParser()
        )
        return await chain.ainvoke(msg)
    

