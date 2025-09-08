from speak_note.manager.chat_manager import ChatManager
from speak_note.manager.context_manager import ContextManager
from speak_note.manager.user_manager import UserManager

from flask import Flask, request, jsonify
import asyncio
import time

class App:
    def __init__(self):
        self.user_manager = UserManager()
        self.context_manager = ContextManager()
        self.chat_manager = ChatManager()

    def create_user(self, user_info=None):
        # user_info(dict): 확장 가능. 예: {"name":..., ...}
        user = self.user_manager.create_user()
        return user

    async def create_chats(self, tasks, max_process_num: int, patient: int):
        """
        tasks: list[{user_id, docs_path}]
        - max_process_num: 동시 실행 최대 개수 (비동기 세마포어로 제한)
        - patient: 대기허용시간(초), 그 시간 내로 max_process_num이 안차면 바로 실행
        """
        semaphore = asyncio.Semaphore(max_process_num)
        start_time = time.time()
        contexts = []

        async def process_task(task):
            async with semaphore:
                ctx = await self.context_manager._create_context_task(task['user_id'], task['docs_path'])
                chat = self.chat_manager.create_chat(user_id=task['user_id'], context=ctx)
                # 유저 객체에 chat, context append
                user = self.user_manager.find_instance(task['user_id'])
                if user:
                    user.chats.append(chat)
                    user.contexts.append(ctx)
                return chat

        pending = []
        for task in tasks:
            pending.append(process_task(task))

            # patient 초 이내에 max_process_num에 도달하지 못하면, 현재까지 모인 작업을 먼저 실행
            if len(pending) >= max_process_num:
                await asyncio.gather(*pending)
                pending = []

            elif (time.time() - start_time) > patient:
                await asyncio.gather(*pending)
                pending = []
                start_time = time.time()

        # 남은 작업 처리
        if pending:
            await asyncio.gather(*pending)

        return True

    async def test_multiple_chat_invoke(self, tasks, max_process_num: int, patient: int):
        """
        tasks: list[{chat_id: msg}]
        - max_process_num, patient: 동시실행/대기 정책 동일.
        """
        semaphore = asyncio.Semaphore(max_process_num)
        results = []
        start_time = time.time()

        async def process_task(chat_id, msg):
            async with semaphore:
                reps = await self.chat_manager.multiple_chat_invoke([{chat_id: msg}])
                # user 찾아서 chat_history에 append
                chat = self.chat_manager.find_chat(chat_id)
                if chat:
                    user = self.user_manager.find_instance(chat.user_id)
                    if user:
                        user.chat_history.extend(reps)
                return reps

        pending = []
        for task in tasks:
            for chat_id, msg in task.items():
                pending.append(process_task(chat_id, msg))

            if len(pending) >= max_process_num:
                batch = await asyncio.gather(*pending)
                results.extend(batch)
                pending = []

            elif (time.time() - start_time) > patient:
                batch = await asyncio.gather(*pending)
                results.extend(batch)
                pending = []
                start_time = time.time()

        # 남은 작업 처리
        if pending:
            batch = await asyncio.gather(*pending)
            results.extend(batch)

        return results

# 실제 Flask app 서버와 연동은 아래처럼 사용 가능
# app = App()
# Flask에서 엔드포인트별로 위 메서드 호출 가능
