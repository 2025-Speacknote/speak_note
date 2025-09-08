from speak_note.manager.manager import Manager
from speak_note.instance.user import User

class UserManager(Manager):
    def __init__(self):
        super().__init__()

    def create_user(self):
        user = User()
        self.create_instance(user)
        return user

    # 필요한 경우 유저 특화 메서드 추가
