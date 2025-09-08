import time
import uuid

from speak_note.instance.chat import Chat
from speak_note.instance.message import Message
from speak_note.instance.context import Context 
from speak_note.instance.instance import Instance

class User(Instance):
    def __init__(self):
        # self.id = uuid.uuid4() # 현재 생성시간.
        super().__init__()
        self.contexts = []   # 유저가 사용한, context id들 목록
        self.chats = []     # 유저가 사용한, 채팅 id들 목록
        self.chat_history = []
    
    def set_chat(self, chat):
        self.chat = Chat

    def add_chat_history(self, message: Message):
        self.chat_history.append(message)