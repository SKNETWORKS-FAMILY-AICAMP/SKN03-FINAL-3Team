import json
import openai

# 복합 질문인지 아닌지 판단 + 의도 파악 + 원래 질문
# 어떤 양식 쓸지 판단 + 의도 + 원래 질문
#
def classify_and_summarize_question(prompt):
    """
    주어진 질문을 분류(HR/NHR)하고 요약하는 함수.
    """
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a chatbot that classifies and summarizes user questions."},
            {"role": "user", "content": prompt}
        ],
        functions=[
            {
                "name": "classify_question",
                "description": "Classify the question as HR-related or NHR-related, and provide a summary.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["HR", "NHR"],
                            "description": "The classification of the question."
                        },
                        "summary": {
                            "type": "string",
                            "description": "A brief summary of the question."
                        },
                    },
                    "required": ["category", "summary"]
                },
            }
        ],
        function_call="auto"
    )

    # Extract the AI response
    chat_response = response["choices"][0]["message"]

    # Extract function_call details
    if "function_call" in chat_response:
        function_call_arguments = json.loads(chat_response["function_call"]["arguments"])
        category = function_call_arguments.get("category", "Unknown")
        summary = function_call_arguments.get("summary", "No summary provided.")
    else:
        category = "Unknown"
        summary = "No summary provided."


    return {
        "hr_category": category,
        "summary": summary.strip(),
    }


def response_openai_function_calling(question):
    responses = []
    result = classify_and_summarize_question(question)

    # 응답 저장
    responses.append({
        "질문": question,
        **result
    })
    return responses