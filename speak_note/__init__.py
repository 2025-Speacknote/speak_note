import os
from dotenv import load_dotenv

# 루트 디렉토리 기준으로 env 경로 설정
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

''' 
myRAG_ver2/speak_note
__init__.py     __pycache__     app.py          chattings       prompts         test.py         tools           work_flows

./chattings:
chat.py

./prompts:
__init__.py     prompt.py

        # ./prompts/__init__.py 소스코드내용.
        from .prompt import *  # 또는 실제 내부 변수/함수명


./tools:
__init__.py     __pycache__     context.py      llms.py         myPDFparser.py

    # ./tools/__init__.py 소스코드내용.
    from .context import Context, context_configs, retriever_configs
    from .llms import basic_RAG, llm_list
    from .myPDFparser import upstageParser2Document  # 함수 이름이 다르면 실제 이름에 맞게 수정
    from langchain_teddynote import logging
    import os
    from dotenv import load_dotenv
    api_key = os.getenv("UPSTAGE_API_KEY")
    api_key = os.getenv("OPENAI_API_KEY")
    load_dotenv()

./work_flows:
__init__.py     basic_CRAG.py   basic_RAG.py

    # ./work_flows/__init__.py 소스코드내용.
    from work_flows import create_crag_chain
    from work_flows import basic_RAG


myRAG_ver2/
app.py

    # myRAG_ver2/app.py의 파일내용.
    import speak_note.tools.llms as llms
    import speak_note.work_flows.basic_RAG as rag
    import speak_note.work_flows.basic_CRAG as crag
    import speak_note.tools.myPDFparser as myPDFparser
    import speak_note.tools.context as context


    document_path = "/Users/yujin/Desktop/코딩shit/python_projects/myRAG_ver2/data/sample_AI_Brief.pdf"
    # GPT context
    gpt_ctx = context.Context(document_path)
    gpt_ctx.set_context(**context.context_configs["gpt"])
    gpt_ctx.set_retriever(context.retriever_configs["balanced"])

    # Upstage context
    upstage_ctx = context.Context(document_path)
    upstage_ctx.set_context(**context.context_configs["upstage"])
    upstage_ctx.set_retriever(context.retriever_configs["balanced"])

    # RAG 체인 등록
    RAG_chains = {
        "gpt_RAG": rag.basic_RAG(gpt_ctx.get_retriever()),
        "upstage_RAG": rag.basic_RAG(upstage_ctx.get_retriever())
    }
    rag_pipeline = RAG_chains["gpt_RAG"]
    llm = llms.llm_list["gpt-4o-mini"]

    work_chain = crag.create_work_chain(llm=llm, rag_pipeline=rag_pipeline)
    response = work_chain.invoke("연애프로 모태솔로지만 연애를 하고싶어에 대해서 알려줘.").content
    print(response)

# 문제상황.
1. llm을 불러오는 코드는 llms.py, myPDFparser.py이다. 다른 모듈은 llms.py, myPDFparser.py를 import해서 쓴다. 이때 .env 파일과, 환경변수 파일은 어디에서 존재하면 되는가?
2. import 에러를 해결하라. 아래는 import에러 메세지이다.

Traceback (most recent call last):
  File "/Users/yujin/Desktop/코딩shit/python_projects/myRAG_ver2/app.py", line 1, in <module>
    import speak_note.tools.llms as llms
  File "/Users/yujin/Desktop/코딩shit/python_projects/myRAG_ver2/speak_note/tools/__init__.py", line 2, in <module>
    from .llms import basic_RAG, llm_list
ImportError: cannot import name 'basic_RAG' from 'speak_note.tools.llms' (/Users/yujin/Desktop/코딩shit/python_projects/myRAG_ver2/speak_note/tools/llms.py)


'''