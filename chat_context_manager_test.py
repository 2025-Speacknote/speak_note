from speak_note.manager.chat_manager import ChatManager
from speak_note.manager.context_manager import ContextManager
import asyncio

# 1. ContextManager로 여러 Context 생성 (이미 네가 테스트해서 정상 작동)
context_manager = ContextManager()
tasks = [
    {"user_id": "user1", "docs_path": "/Users/yujin/Desktop/코딩shit/python_projects/myRAG_ver2/data/sample_AI_Brief.pdf"},
    {"user_id": "user2", "docs_path": "/Users/yujin/Desktop/코딩shit/python_projects/myRAG_ver2/data/sample_AI_Brief.pdf"},
]
contexts = asyncio.run(context_manager.create_context(tasks))

# 2. ChatManager로 여러 Chat 생성
from speak_note.manager.chat_manager import ChatManager
chat_manager = ChatManager()
chat1 = chat_manager.create_chat(user_id="user1", context=contexts[0])
chat2 = chat_manager.create_chat(user_id="user2", context=contexts[1])

# 3. 복수의 채팅 입력(질문) 비동기 테스트
async def test_multiple_chat_invoke():
    tasks = [
        {chat1.id: "적분의 기본정리(FTC)는 무엇인가?"},
        {chat2.id: "G7은 AI에 대해서 어떤 합의를 했지?"}
    ]
    reps_list = await chat_manager.multiple_chat_invoke(tasks)
    for reps in reps_list:
        print("채팅 ID:", reps.chat_id)
        print("유저 ID:", reps.user_id)
        print("답변:", reps.contents)
        print("="*30)

# 4. 실행
asyncio.run(test_multiple_chat_invoke())
