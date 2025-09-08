import asyncio
import speak_note.tools.llms as llms
import speak_note.work_flows.RAG as rag
from speak_note.chattings.chat import Chat, en_Chat
from speak_note.work_flows.basic_CRAG import CRAG, en_CRAG
import speak_note.tools.myPDFparser as myPDFparser
import speak_note.tools.en_myPDFparser as en_myPDFparser
import speak_note.instance.context as context


class app():   
    # 서버와 연동해서 전체적인 앱동작 정의.       
    # 서버에서의 text를 모아서, 일정시간 또는 일정량이 넘으면 flush()
    # flush(list[str]) -> str API를 갖고있어야한다.
    def __init__(self):
        ...


    def flush(stt_texts : list[str]) -> list[str]:
        ...


class ChatManager():
    # 채팅을 관리한다.
    # 채팅은 고유한 아이디를 갖도록 한다.
    # Chat - (Context, chat_id, text)
    # Context가 업데이트 될때마다 DB에 해당 채팅의 정보저장.
    # Context가, chat_id 만으로 채팅 복구할수있게 해야함.
    def __init__(self):
        ...

    async def ainvoke(self, chat_id, text):
        ...


#############################################################################################################
#                                                                                                           #
#                                                                                                           #
#                                                                                                           #
#                                                                                                           #
#############################################################################################################
#                                                                                                           #
# document_path1 = "data/sample_AI_Brief.pdf"                                                               #
# document_path2 = "data/10 Vector Calculus.pdf"                                                            #
#                                                                                                           #
#############################################################################################################
#                                                                                                           #
# chat_list = {                                                                                             #
#             "a": Chat("a"),                                                                               #
#             "b": Chat("b")                                                                                #   
#              }                                                                                            #  
#                                                                                                           #  
#############################################################################################################
#                                                                                                           #
# chat_list["en_a"] = en_Chat("en_a")                                                                       #
# chat_list["en_a"].set_document(document_path1).set_work_chain()                                           #
# response = chat_list["a"].set_document(document_path1).set_work_chain()                                   #
# print("-------------------------- gpt only ----------------------------")                                 #
#                                                                                                           #
#############################################################################################################
#
# gpt_only = asyncio.run(llms.llm_list["gpt-4o-mini"].ainvoke("AI 위험관리를 위해 세계는 어떤걸 규정했어?"))                 
# print(gpt_only)                                                                                       
# print()                                                                                              
# print("-------------------------- crag ----------------------------")
#
#############################################################################################################
#                                    
# crag = asyncio.run(chat_list["a"].ainvoke("a", "AI 위험관리를 위해 세계는 어떤걸 규정했어?"))                   
# print(crag)                                                                                           
# print()                                                                                                 
# print("-------------------------- en_crag ----------------------------")
#
#############################################################################################################
#                                
# en_crag = asyncio.run(chat_list["en_a"].ainvoke("en_a", "AI 위험관리를 위해 세계는 어떤걸 규정했어?"))          
# print(en_crag)                                                                                        
# print()                                                                                               
# print("-------------------------- crag wrong id ----------------------------")
#
#############################################################################################################
#                           
# crag_wrong_id = asyncio.run(chat_list["a"].ainvoke("b", "AI 위험관리를 위해 세계는 어떤걸 규정했어?"))         
# print(crag_wrong_id)                                                                                  
# print()                                                                                               
#
#############################################################################################################
#
# print("-------------------------- crag no chain ----------------------------")                        
# crag_no_chain = asyncio.run(chat_list["b"].ainvoke("a", "AI 위험관리를 위해 세계는 어떤걸 규정했어?"))          
# print(crag_no_chain)                                                                                       
#
#############################################################################################################
#                                                                                                           #
#                                                                                                           #
#                                                                                                           #
#                                                                                                           #
#############################################################################################################