from speak_note.engine.app import App
import asyncio

if __name__ == "__main__":
    app = App()

    # 1. 유저 생성 (2명)
    user1 = app.create_user()
    user2 = app.create_user()
    print("생성된 user id:", user1.id, user2.id)

    # 2. 여러 Context/Chat 생성 (각 유저별로 문서 1개씩)
    context_tasks = [
        {"user_id": user1.id, "docs_path": "/Users/yujin/Desktop/코딩shit/python_projects/myRAG_ver2/data/10 Vector Calculus.pdf"},
        {"user_id": user2.id, "docs_path": "/Users/yujin/Desktop/코딩shit/python_projects/myRAG_ver2/data/sample_AI_Brief.pdf"}
    ]
    # 비동기 실행
    asyncio.run(app.create_chats(context_tasks, max_process_num=2, patient=2))

    # 3. 방금 만든 Chat 목록/ID 확인 (각 유저별로 1개씩 있다고 가정)
    chats = []
    for user in [user1, user2]:
        # user.chats는 UserManager/ChatManager 연동에 따라 id 또는 객체 리스트일 수 있음
        # ChatManager에서 id로 찾아서 객체 반환하는 방식 추천
        if hasattr(user, "chats") and len(user.chats) > 0:
            for c in user.chats:
                if hasattr(c, "id"):
                    chats.append(c)
                else:
                    chat_obj = app.chat_manager.find_chat(c)  # id라면 객체로 변환
                    if chat_obj:
                        chats.append(chat_obj)
    print("생성된 chat id:", [c.id for c in chats])

    # 4. 여러 채팅에 동시 메시지 입력 비동기 테스트
    chat_tasks = [
        {chats[0].id: "적분의 기본정리(FTC)를 설명해줘."},
        {chats[1].id: "G7은 AI에 대해서 어떤 합의를 했지?"}
    ]
    results = asyncio.run(app.test_multiple_chat_invoke(chat_tasks, max_process_num=2, patient=2))

    # 5. 결과 출력 (Message 객체 리스트)
    for reps in results:
        # reps가 리스트(여러개)일 수도, 단일 Message일 수도 있음
        if isinstance(reps, list):
            for r in reps:
                print("채팅 ID:", r.chat_id, "| 유저 ID:", r.user_id, "| 답변:", r.contents)
        else:
            print("채팅 ID:", reps.chat_id, "| 유저 ID:", reps.user_id, "| 답변:", reps.contents)

    # 6. 각 유저의 chat_history 확인
    for user in [user1, user2]:
        print(f"\nUser {user.id}의 채팅 히스토리:")
        for msg in getattr(user, "chat_history", []):
            print(msg.contents)
