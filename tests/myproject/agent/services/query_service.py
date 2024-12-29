import re
from agent.utils.sql_validator import validate_and_execute_sql


def extract_sql_query(sllm_response: str) -> str:
    match = re.search(r"SQL 쿼리:\n(.+)", sllm_response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def execute_sllm_generated_query(sql_query: str, user_id: str):
    # {user_id} 템플릿 치환
    if "{user_id}" in sql_query:
        sql_query = sql_query.replace("{user_id}", user_id)
    return validate_and_execute_sql(sql_query)
