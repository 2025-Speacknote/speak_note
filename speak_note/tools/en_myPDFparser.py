'''
upstage parser를 이용해서, document 형식에 맞게 시퀀셜 자연어 형태로 pdf내용을 읽어온다.
'''
import os
import requests
import asyncio
import time  
import httpx
from bs4 import BeautifulSoup
from openai import OpenAI # openai==1.52.2
from typing import Callable, Dict
from langchain.schema import Document
from collections import defaultdict
from langchain_teddynote import logging


from langchain.prompts import PromptTemplate
from langchain.schema import Document
from langchain_core.output_parsers import StrOutputParser

from dotenv import load_dotenv

import speak_note.prompts.english_prompt as prompt
import speak_note.tools.llms as llms

api_key = os.getenv("UPSTAGE_API_KEY")
# API 키를 환경변수로 관리하기 위한 설정 파일
# load_dotenv() # API 키 정보 로드

llm = llms.llm_list["solar-pro"]

def text_handler(figure_data: dict | None) -> str:
    if figure_data is None or not isinstance(figure_data, dict):
        return ""
    try:
        html = figure_data.get("content", {}).get("html", "")
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        img = soup.find("img")
        if img and img.get("alt"):
            alt_text = img.get("alt").strip()
            return f"markdown: {alt_text}, text: {alt_text}"
        return soup.get_text(separator="\n", strip=True)
    except Exception:
        return ""


async def equation_handler(equation_data_raw: tuple):
    prompt_template = PromptTemplate(
        input_variables=["equation_descript_text", "question"],
        template=prompt.equation_handler_prompt
    )

    equation_data = equation_data_raw[0]
    equation_descript_text = text_handler(equation_data_raw[1])  # 설명 문장 (텍스트 주변 문맥)
    markdown = equation_data["content"].get("markdown", "").strip()
    text = equation_data["content"].get("text", "").strip()
    question = f"markdown: {markdown}, text: {text}"

    chain = (
        prompt_template
        | llm
        | StrOutputParser()
    )

    return await chain.ainvoke({
        "equation_descript_text": equation_descript_text,
        "question": question
    })

async def chart_handler(chart_data_raw: tuple):
    # 프롬프트 템플릿 구성
    prompt_template = PromptTemplate(
        input_variables=["chart_descript_text", "question"],
        template=prompt.chart_handler_prompt
    )

    # 입력 구성
    chart_data = chart_data_raw[0]["content"]["html"]
    chart_descript_text = text_handler(chart_data_raw[1])

    # Chain 생성
    chain = prompt_template | llm | StrOutputParser()

    return await chain.ainvoke({
        "chart_descript_text": chart_descript_text,
        "question": chart_data
    })


async def figure_handler(figure_data: tuple):
    prompt_template = PromptTemplate(
        input_variables=["figure_description", "question"],
        template=prompt.figure_handler_prompt
    )

    html_content = figure_data[0]["content"]["html"]
    figure_description = text_handler(figure_data[1])

    chain = prompt_template | llm | StrOutputParser()

    return await chain.ainvoke({
        "figure_description": figure_description,
        "question": html_content
    })

category_to_handler: Dict[str, Callable] = {
    "equation": equation_handler,
    "chart": chart_handler,
    "figure": figure_handler,
}


async def parse_data_by_category(data):
    category = data[0]['category'] if isinstance(data, tuple) else data['category']
    handler = category_to_handler.get(category, lambda x: text_handler(x))
    if asyncio.iscoroutinefunction(handler):
        return await handler(data)
    else:
        return handler(data)


def find_nearest_context_text(datas, current_index, max_search_num=6):
    for offset in range(1, max_search_num):
        idx = current_index - offset
        if idx >= 0:
            text = text_handler(datas[idx])
            if text.strip():
                return text
    for offset in range(1, max_search_num):
        idx = current_index + offset
        if idx < len(datas):
            text = text_handler(datas[idx])
            if text.strip():
                return text
    return ""


async def group_by_page_with_handlers(datas):
    page_texts = defaultdict(list)
    for i, element in enumerate(datas):
        page = element.get("page", -1)
        category = element.get("category", "")
        if category in ["chart", "figure", "equation"]:
            context_text = find_nearest_context_text(datas, i)
            pair = (element, {"content": {"html": context_text}} if context_text else None)
            parsed_text = await parse_data_by_category(pair)
        else:
            parsed_text = await parse_data_by_category(element)
        page_texts[page].append(parsed_text)
    return [
        {"page": page, "content": "\n".join(texts)}
        for page, texts in sorted(page_texts.items())
    ]


def convert_grouped_pages_to_documents(grouped_pages):
    return [Document(page_content=p["content"], metadata={"page": p["page"]}) for p in grouped_pages]


async def upstageParser2Document(file_path):
    start = time.perf_counter()
    print(f"[PARSER] parsing 시작: {file_path}", flush=True)

    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            response = await client.post(
                "https://api.upstage.ai/v1/document-digitization",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"document": f},
                data={
                    "ocr": "force",
                    "coordinates": False,
                    "chart_recognition": True,
                    "output_formats": '["html"]',
                    "base64_encoding": '["table"]',
                    "model": "document-parse"
                }
            )
    datas = response.json()["elements"]
    grouped_pages = await group_by_page_with_handlers(datas)
    result = convert_grouped_pages_to_documents(grouped_pages)
    end = time.perf_counter()
    print(f"[PARSER] parsing 완료: {file_path} / 소요시간: {end - start:.2f}초", flush=True)

    return result


# if __name__ == "__main__":
#     file_path = "data/10 Vector Calculus.pdf"
#     documents = asyncio.run(upstageParser2Document(file_path))
#     for doc in documents:
#         print(f"[page {doc.metadata['page']}] {doc.page_content[:100]}...")
