''' 
현재는 linear한 탐색으로 객체에 접근한다.
파일이 매우 많아지면, 해시로 바꾸거나, 이진탐색으로 log(N)으로 탐색 줄여보자.
'''
from speak_note.instance.instance import Instance

class Manager:
    def __init__(self):
        # 모든 인스턴스는 리스트로 관리
        self.instances = []

    def create_instance(self, instance: Instance):
        self.instances.append(instance)
        return instance.id

    def delete_instance(self, instance_id: str):
        for i, inst in enumerate(self.instances):
            if inst.id == instance_id:
                del self.instances[i]
                return True
        return False

    def find_instance(self, instance_id: str):
        for inst in self.instances:
            if inst.id == instance_id:
                return inst
        return None

    def all_instances(self):
        return self.instances

    def clear_all(self):
        self.instances.clear()
