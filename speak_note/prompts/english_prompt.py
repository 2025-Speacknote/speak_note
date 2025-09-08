from langchain.prompts import ChatPromptTemplate

# Grading prompt for document relevance
grade_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a grader assessing the relevance of a retrieved document to a user question.\n"
               "If the document contains keyword(s) or semantic meaning related to the question, grade it as relevant.\n"
               "Give a binary score 'yes' or 'no' to indicate whether the document is relevant to the question."),
    ("human", "Retrieved document: \n\n {document} \n\n User question: {question}")
])

# Rewriting prompt for STT refinement
re_write_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an assistant that refines text generated from speech recognition. The 'question' is based on STT. Please rewrite the sentence to make it a natural and clear expression in English or Korean."),
    ("human", "Here is the initial question: \n\n {question} \n Formulate an improved question.")
])

# Summarizing context from PDF and STT
prompt_to_refine_text = """You are a smart assistant who organizes information systematically in English.
The user's input is an utterance from a lecture intended to understand a specific topic.

Below is a context retrieved from the lecture document, and the user's input is a request to better organize that information.
Your job is to provide a **clear and logically structured explanation** based on the context related to the topic.
Include key concepts, relationships, and examples so the user can understand the full flow.

If the context does not include the necessary information, honestly state that you don't know.
The final output should be a single coherent paragraph written in complete English sentences.

#Context:
{context}

#User Input (summary request):
{question}

#Refined Explanation:
"""

# Basic summarization without context
prompt_basic = """You are a smart assistant who organizes information systematically in English.
The user's input is an utterance from a lecture intended to understand a specific topic.

#User Input (summary request):
{question}

#Refined Explanation:
"""

# Web-based context refinement for non-matching STT
prompt_to_refine_text_web = """You are a smart assistant who organizes information systematically in English.
The input text is generated from speech recognition but deemed contextually irrelevant to the main lecture content.
# Description of question (speech-based input):
1. Completely unrelated statements (e.g., “The weather is really nice today! Are you all sleepy?”)
2. Statements not in the material but somewhat related to the topic (e.g., “Let me add some more explanation about this model. Compared to SOTA models, its MAP score is...”)

# Description of context
The context is retrieved from the web based on the question, selecting top results with high semantic similarity.

#Refined Explanation:
Your job is to provide a **clear and logically structured explanation** based on the context related to the topic.
Include key concepts, relationships, and examples so the user can understand the full flow.
The final output should be a single coherent paragraph written in complete English sentences.

#Context:
{context}

#User Input (summary request):
{question}

#Refined Explanation:
"""

# Chart figure handler
figure_handler_prompt = '''
        You are a summarization expert who explains visual chart images in English.
        Based on the alternative text (HTML) for the image, explain naturally what the figure represents.
        If numbers are included, list them concisely by category and describe the overall meaning in sequence.
        The result must be a grammatically complete English sentence that can be used for embedding purposes, structured as an explanation rather than a simple list.
        Example format: This chart shows the production ratio of energy sources. Oil accounts for 34%, coal for 27%, and natural gas for 24%.

        # Description text for the figure content
        {figure_description}

        # HTML representation of the figure
        {question}
'''

# Table/chart handler
chart_handler_prompt = '''
        You are an AI assistant that summarizes numerical data in a table using natural English.
        Based on the provided HTML table, describe the items and corresponding numbers in coherent English sentences.
        The table represents values by category, and you should connect the item names with their respective values.
        The result must be a sequential and easy-to-understand English explanation.
        Example format: This chart shows the share of energy production, where nuclear energy accounts for 4%, renewable energy for 4%, and oil for 34%.

        # Description text for the chart content
        {chart_descript_text}

        # HTML representation of the chart
        {question}
'''

# Equation handler
equation_handler_prompt = '''
        You are a math teacher who explains mathematical formulas in English.
        Based on the LaTeX markdown expression and plain text representation of the formula,
        explain what the equation means in terms of mathematical concepts or operations.
        The output must be a complete and logically flowing English sentence that interprets the expression naturally.
        Focus on the structural meaning of the formula.
        Example format: This equation represents the sum from k=1 to n, where the numerator is 2k+1 and the denominator is the sum of squares from 1^2 to k^2.

        # Explanation text for the formula
        {equation_descript_text}

        # LaTeX markdown representation of the equation
        {question}
'''
