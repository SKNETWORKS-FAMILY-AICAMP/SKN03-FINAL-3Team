# agent/services/query_service.py

import logging
from agent.services.ollama_service import query_ollama_nl2sql
from agent.services.format_service import get_formatted_response

logger = logging.getLogger("agent")


def execute_nl2sql_flow(
    user_message: str,
    user_info: dict,
    access_level: str,
    extract_sql_func,
    is_sql_permitted_func,
) -> str:
    """
    1) user_message + access_level 이용해 nl2sql prompt 생성
    2) Ollama로 nl2sql 모델 호출
    3) SQL 추출 => 권한 체크 => DB 실행 => 결과 포맷팅
    """
    rank_name = user_info.get("rank_name")
    slack_id = user_info.get("slack_id")

    nl2sql_prompt = f"""
사용자 직급: {rank_name}
접근 레벨: {access_level}
원본 질문: {user_message}

절대 권한 범위를 넘어서는 테이블/칼럼은 사용하지 말고,
테이블/칼럼이 불분명하면 "cannot_generate_sql"을 반환하십시오.
"""
    try:
        nl2sql_response = query_ollama_nl2sql(
            prompt=nl2sql_prompt,
            # model_name="my-nl2sql-model" (단일 서버 + multi model일 경우)
            temperature=0.0,
            max_tokens=512,
        )
        logger.debug(f"[execute_nl2sql_flow] raw_sql_response = {nl2sql_response}")
    except Exception as e:
        logger.error(f"nl2sql 모델 호출 실패: {e}", exc_info=True)
        return "죄송합니다. DB 쿼리를 생성하는 중 오류가 발생했습니다."

    generated_sql = extract_sql_func(nl2sql_response)
    if not generated_sql or "cannot_generate_sql" in generated_sql.lower():
        logger.warning("[execute_nl2sql_flow] 올바른 SQL 생성 불가")
        return "죄송합니다. 해당 질의에 대한 SQL을 생성할 수 없습니다."

    # 권한 체크
    if not is_sql_permitted_func(generated_sql, access_level):
        logger.warning(f"SQL 권한 부족: {generated_sql} (access_level={access_level})")
        return "죄송합니다. 해당 데이터 조회 권한이 없습니다."

    # DB 쿼리 실행 (실제 MySQL 연동 가정)
    try:
        query_result = execute_sllm_generated_query(generated_sql, slack_id)
    except Exception as e:
        logger.error(f"MySQL 쿼리 실행 실패: {generated_sql}, 에러: {e}", exc_info=True)
        return "죄송합니다. DB 조회 도중 에러가 발생했습니다."

    if isinstance(query_result, str) and query_result.startswith("ERROR"):
        logger.error(f"MySQL 쿼리 실행 에러: {query_result}")
        return "죄송합니다. DB 조회 중 문제가 생겼습니다."

    # 결과 포맷팅
    try:
        formatted_response = get_formatted_response(
            rank_name, user_message, query_result
        )
    except Exception as e:
        logger.error(f"결과 포맷팅 실패: {e}", exc_info=True)
        return "죄송합니다. DB 조회 결과를 포맷팅하던 중 오류가 발생했습니다."

    return formatted_response


def execute_sllm_generated_query(sql_query: str, slack_id: str):
    """
    실제 DB(MySQL 등)에 쿼리를 실행하는 함수.
    여기서는 예시로 성공/에러 케이스만 가정함.
    """
    logger.info(f"[execute_sllm_generated_query] Executing SQL: {sql_query}")
    # 실제 DB 접근 로직 필요
    # 예: conn.execute(sql_query)
    # return rows or "ERROR:..."
    return [
        {"name": "홍길동", "department": "개발팀", "email": "hong@example.com"},
        {"name": "김영희", "department": "영업팀", "email": "kim@example.com"},
    ]
