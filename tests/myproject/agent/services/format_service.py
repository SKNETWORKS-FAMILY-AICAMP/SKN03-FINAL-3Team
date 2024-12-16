from agent.utils.sllm_client import query_sllm


def extract_response_format(user_input: str) -> str:
    if "표로" in user_input or "테이블로" in user_input:
        return "table"
    elif "마크다운" in user_input:
        return "markdown"
    else:
        return "text"


def generate_response_prompt(
    user_role: str, user_input: str, response_format: str, query_result
) -> str:
    return f""" 
    사용자 역할: {user_role}
    질문: {user_input}
    응답 형식: {response_format}
    데이터베이스 결과: {query_result}
    이를 {response_format} 형식으로 보기 좋게 정리해주세요.
    """


def get_formatted_response(user_role: str, user_input: str, query_result):
    response_format = extract_response_format(user_input)
    prompt = generate_response_prompt(
        user_role, user_input, response_format, query_result
    )
    return query_sllm(prompt)
