from typing import Optional
from speak_note.instance.instance import Instance
import uuid


class Message(Instance):
    # 이 앱 내에서, 어떤 유저, 어떤 채팅에서 생성됐는지 정보가 있는 컨테이너 객체.
    def __init__(self, contents,user_id: Optional[str] = None, chat_id: Optional[str] = None):
        # self.id = uuid.uuid4()
        super().__init__()
        self.contents = contents    # 딕셔너리 형태로 
        # content["generation"] : chain답변
        # content["question"]   : 사용자질의
        
        # user_id, chat_id는 각각 uuid4()로 생성된 고유 id, 이들이 있을땐, 이 객체가 그 정보를 저장한다. 기본적으로 일단 존재는한다.
        self.user_id = user_id
        self.chat_id = chat_id
