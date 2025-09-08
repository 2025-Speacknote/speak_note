from speak_note.manager.manager import Manager
from speak_note.instance.chat import Chat
from speak_note.instance.message import Message
import asyncio
import time

class ChatManager(Manager):
    def __init__(self):
        super().__init__()

    def create_chat(self, user_id, context):
        chat = Chat(user_id=user_id, context=context)
        self.create_instance(chat)
        return chat

    def find_chat(self, chat_id):
        # id로 chat 객체 조회
        for inst in self.instances:
            if isinstance(inst, Chat) and inst.id == chat_id:
                return inst
        return None

    async def _ainvoke_chat(self, chat: Chat, msg: str):
        # 실제 채팅 비동기 호출. Message 객체로 감싸서 반환.
        reps = await chat.ainvoke(chat.id, msg=msg)
        # reps가 이미 Message면 그대로, 아니면 래핑
        if isinstance(reps, Message):
            reps.chat_id = chat.id
            reps.user_id = chat.user_id
            return reps
        else:
            # reps가 str 등인 경우 Message로 래핑
            return Message(
                contents={"generation": reps, "question": msg},
                user_id=chat.user_id,
                chat_id=chat.id
            )

    async def multiple_chat_invoke(self, tasks):
        '''
        tasks: list of dict, [{chat_id: msg}]
        return: list of Message (reps)
        '''
        start_time = time.time()
        async_tasks = []
        for task in tasks:
            for chat_id, msg in task.items():
                chat = self.find_chat(chat_id)
                if chat is not None:
                    async_tasks.append(self._ainvoke_chat(chat, msg))
                else:
                    # chat_id 못찾은 경우 빈 Message 생성 (실패 기록용)
                    async_tasks.append(
                        Message(
                            contents={"generation": None, "question": msg, "error": "chat_not_found"},
                            user_id=None,
                            chat_id=chat_id
                        )
                    )

        reps_list = await asyncio.gather(*async_tasks)
        print(f"전체 {len(tasks)}개의 채팅 메시지 처리 시간: {time.time() - start_time:.2f}초")
        return reps_list
