from speak_note.work_flows.basic_CRAG import CRAG, en_CRAG
from speak_note.instance.message import Message
from speak_note.instance.context import Context
from speak_note.instance.instance import Instance


class Chat(Instance):
    def __init__(self, context : Context, user_id):   
        # self.id = uuid.uuid4()     # 본인 생성시간.
        super().__init__()
        self.context = context
        self.user_id = user_id
        self.RAG_chain = context.basic_RAG
        self.set_work_chain()
        

    def set_work_chain(self, work_chain = None):
        if work_chain == None:
            self.work_chain = CRAG(rag_pipeline=self.RAG_chain)
        else :
            self.work_chain = work_chain
    
    
    async def ainvoke(self, id:str, msg:str):
        if self.work_chain == None:
            print("you should set work chain first.")
            return
        
        if id != self.id :
            print("id not matched")
            return
        else : 
            result = await self.work_chain.ainvoke(msg)
            reps_msg = Message(contents=result, chat_id=self.id)
            return reps_msg



# class en_Chat(Chat):
#     async def set_document(self, document_path : str):
#         self.documnet_path_list.append(document_path)
#         self.cur_document_path = document_path

#         # GPT context
#         gpt_ctx = await context.en_Context.create(document_path)
#         gpt_ctx.set_context(**context.context_configs["gpt"])
#         gpt_ctx.set_retriever(context.retriever_configs["balanced"])

#         # Upstage context
#         upstage_ctx = await context.en_Context.create(document_path)
#         upstage_ctx.set_context(**context.context_configs["upstage"])
#         upstage_ctx.set_retriever(context.retriever_configs["balanced"])

#         # RAG 체인 등록
#         RAG_chains = {
#             "gpt_RAG": rag.en_RAG(gpt_ctx.get_retriever()),
#             "upstage_RAG": rag.en_RAG(upstage_ctx.get_retriever())
#         }
#         self.RAG_chains = RAG_chains
#         return self



#     def set_work_chain(self, work_chain = None):
#         # work_chain : invoke(str) 라는 공통 API를 갖는 객체여야한다.
#         if self.RAG_chains == None:
#             print("document not ready, you should invoke set_document before set work chain.")
#             return
        
#         if work_chain == None:
#             self.work_chain = en_CRAG(rag_pipeline=self.RAG_chains["gpt_RAG"])
#         else :
#             self.work_chain = work_chain







    
