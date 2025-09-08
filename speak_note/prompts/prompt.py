from langchain.prompts import ChatPromptTemplate

# main.py


'''
pdf내용과, 음성인식 텍스트의 적합성에 대해서 판단하도록 하는 프롬포트이다.
'''
grade_prompt = ChatPromptTemplate.from_messages([

    ("system", "You are a grader assessing relevance of a retrieved document to a user question.\n"
                "If the document contains keyword(s) or semantic meaning related to the question, grade it as relevant.\n"
                "Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."),
    ("human", "Retrieved document: \n\n {document} \n\n User question: {question}")
])


'''
# question 음성인식 기반으로 생성된 텍스트입니다.



'''
re_write_prompt = ChatPromptTemplate.from_messages([
    ("system", "너는 텍스트를 정제해서 재생성 해주는 어시스턴스야. question은 음성인식 기반으로 생성된 텍스트야. 너는 이 텍스트가 자연스러운 한국어 또는 영어 문장이 되도록 문장을 정제해줘야해. "),
    ("human", "Here is the initial question: \n\n {question} \n Formulate an improved question.")
])


# myUpstageRAG
'''
context 내용을 기반으로 음성 인식 텍스트에 대한 내용을 정리, 요약하게 하는 프롬포트이다.
'''
"""
음성 인식 텍스트에 기반한 강의 내용을 명확히 정리해주는 프롬포트입니다.
"""
prompt_to_refine_text = """당신은 한국어로 정보를 체계적으로 정리해주는 스마트 어시스턴트입니다.
사용자가 말한 내용은 강의 중 특정 주제에 대해 이해하고자 한 것입니다.

아래는 강의에서 추출된 문서형 컨텍스트이며, 사용자의 질문은 그 내용을 보다 잘 정리하고자 한 것입니다.
당신의 역할은 해당 주제에 대해 컨텍스트를 기반으로 **명확하고 논리적인 흐름으로 정리된 설명**을 제공하는 것입니다.
사용자가 전체 흐름을 이해할 수 있도록 중요 개념, 관계, 예시를 적절히 구성해 전달하세요. 

다만, 문서에 해당 정보가 없으면 모른다고 정직하게 말하세요.
최종 출력은 완전한 한국어 문장으로 된 하나의 정리된 설명이어야 합니다.

#Context:
{context}

#User Input (요약 요청 내용):
{question}

#정리된 설명:
"""

prompt_basic = """당신은 한국어로 정보를 체계적으로 정리해주는 스마트 어시스턴트입니다.
사용자가 말한 내용은 강의 중 특정 주제에 대해 이해하고자 한 것입니다.

#User Input (요약 요청 내용):
{question}

#정리된 설명:
"""

# myUpstageRAG
'''
websearch 내용을 기반으로 음성 인식 텍스트에 대한 내용을 정리, 요약하게 하는 프롬포트이다.
'''
prompt_to_refine_text_web = """당신은 한국어로 정보를 체계적으로 정리해주는 스마트 어시스턴트입니다.
음성인식 텍스트는 강의 자료의 문맥과 적합하지 않다고 판단된 문장입니다.
# question 음성인식 기반으로 생성된 텍스트입니다.
1. 발표내용과 아예 무관한 상황. (예시, 오늘 날씨가 너무좋네요! 여러분들 잠오시죠?)
2. 발표내용과 무관하진 않지만, 발표자료에는 있지 않은 정보에 대한 내용일때. (저가 이 모델에 대해서 추가 설명을 좀 드려볼게요. 일단 SOTA모델에 비교해서 이 모델의 MAP점수는...)

# context 설명
question을 기반으로 웹에서 탐색된 내용중 문맥과 유사도가 높은 상위 텍스트를 문맥으로 저장한 상태입니다.

#정리된 설명
당신의 역할은 해당 주제에 대해 컨텍스트를 기반으로 **명확하고 논리적인 흐름으로 정리된 설명**을 제공하는 것입니다.
사용자가 전체 흐름을 이해할 수 있도록 중요 개념, 관계, 예시를 적절히 구성해 전달하세요.
최종 출력은 완전한 한국어 문장으로 된 하나의 정리된 설명이어야 합니다.
#Context:
{context}

#User Input (요약 요청 내용):
{question}

#정리된 설명:
"""



# myPDFparser
'''
도표 이미지 또는 차트이지만 도표로 인식한 여러 데이터에 대해서 임베딩이 가능한 텍스트로 변환하기 위한 프롬프트
'''
figure_handler_prompt = '''
        너는 도표 이미지를 설명하는 한국어 요약 전문가야.
        이미지의 대체 텍스트(html)를 기반으로, 그 이미지가 무엇을 나타내는지 자연스럽게 설명해줘.
        수치가 포함된 경우에는 항목별로 나열하면서 간결하게 수치를 언급해주고, 전체적으로 어떤 내용을 담고 있는지 한국어로 시퀀셜하게 요약해줘.
        결과는 임베딩 벡터로 사용할 수 있도록 완전한 문장 구조를 가져야 하며, 단순 나열이 아닌 설명적인 형태로 구성되어야 해.
        형식 예시: 이 도표는 에너지 자원별 생산 비율을 보여준다. 석유는 34%, 석탄은 27%, 천연가스는 24% 등의 비중으로 구성된다. 

        # 피겨 표 내용에 대한 설명 텍스트
        {figure_description}


        # html 형식의 피겨 내용
        {question}
        '''
    

'''
차트를  임베딩이 가능한 텍스트로 변환하기 위한 프롬프트
'''
chart_handler_prompt = '''
        너는 표에 포함된 수치를 한국어로 요약 설명하는 AI야.
        아래에 제공된 표 내용(html)을 보고, 각 항목과 수치를 한국어 문장으로 자연스럽게 설명해줘.
        표는 항목별 수치를 나타내는 도표이며, 각 항목의 이름과 그에 대응하는 수치를 연결하여 설명해야 해.
        결과는 문장 형태의 한국어 설명이어야 하며, 사람이 쉽게 이해할 수 있는 시퀀셜한 설명으로 구성돼야 해.
        형식 예시: 이 도표는 에너지 생산량 비중을 나타내며, 핵에너지는 4%, 재생에너지는 4%, 석유는 34%의 비중을 차지한다.\
        
        # 차트 표 내용에 대한 설명 텍스트
        {chart_descript_text}
        
        # html 형식의 차트 표 내용
        {question}
    '''


'''
방정식이나 수학적 공식을 임베딩이 가능한 텍스트로 변환하기 위한 프롬프트
'''
equation_handler_prompt = '''
        너는 수학 수식을 설명하는 한국어 선생님이야.
        아래에 주어진 수학 수식의 LaTeX 마크다운(markdown) 표현과 일반 텍스트(text) 표현을 보고, 
        이 수식이 의미하는 수학적 개념 또는 연산 과정을 한국어 자연어 문장으로 간결하게 설명해줘.
        결과 문장은 논리적 흐름을 가지는 완전한 문장이어야 하며, 수학적 표현이 자연스럽게 해석되도록 구성되어야 해.
        수식의 구조적 의미에 초점을 맞춰 설명해줘.
        형식 예시: 이 수식은 k=1부터 n까지의 합을 나타내며, 분자는 2k+1이고 분모는 1^2부터 k^2까지의 제곱합이다.

        # 수식에 내용에 대한 설명 텍스트
        {equation_descript_text}

        # LaTeX 마크다운(markdown) 표현식의 방정식
        {question}
        '''
