from agent.utils.sllm_client import query_sllm
from agent.utils.db_schema import get_db_schema


def generate_cot_prompt(user_input: str, user_role: str, db_schema: str) -> str:
    prompt = f"""
    데이터베이스 스키마:
    {db_schema}

    사용자 역할: {user_role}
    질문: {user_input}
    생각을 단계별로 정리한 뒤, SQL 쿼리를 생성하세요.
    SQL 쿼리는 'SQL 쿼리:'라는 문구 뒤에 작성해주세요.
    """
    return prompt.strip()


def apply_cot(user_input: str, user_role: str) -> str:
    db_schema = get_db_schema()
    prompt = generate_cot_prompt(user_input, user_role, db_schema)
    # 단순화: 복수 응답 필요 없이 하나만 받아옴
    final_response = query_sllm(prompt, num_return_sequences=1)
    return final_response
