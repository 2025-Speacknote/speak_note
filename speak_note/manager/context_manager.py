from speak_note.manager.manager import Manager
from speak_note.instance.context import Context
import asyncio
import time

class ContextManager(Manager):
    def __init__(self):
        super().__init__()

    async def _create_context_task(self, user_id, docs_path):
        # 비동기 Context 생성 (await Context.create)
        context = await Context.create(document_path=docs_path, user_id=user_id)
        self.create_instance(context)
        return context

    async def create_context(self, tasks: list[dict]):
        '''
        tasks: list of dict [{user_id, docs_path}]
        return: list[Context]
        '''
        start_time = time.time()
        async_tasks = [
            self._create_context_task(task['user_id'], task['docs_path'])
            for task in tasks
        ]
        contexts = await asyncio.gather(*async_tasks)
        print(f"총 {len(tasks)}개의 Context 생성 처리 시간: {time.time() - start_time:.2f}초")
        return contexts
