# agent/services/agent_service.py

import logging
from typing import Dict, Any
import re

from agent.services.intent_service import classify_db_need
from agent.services.chat_service import chat_with_agent
from agent.services.query_service import (
    execute_nl2sql_flow,
    restrict_sql_query_by_access,
)

logger = logging.getLogger("agent")

# 여기에 DB 실행 함수(run_sql_query)나, 혹은 ORM 방식 코드가 들어갈 수도 있습니다.
# 예: from agent.services.db_service import run_sql_query


def process_user_message(
    user_message: str,
    user_info: Dict[str, Any],
    access_level: str,
) -> str:
    """
    1) 'DB가 필요한지' 의도 분류 (classify_db_need)
    2) NO_DB -> chat_with_agent()
    3) NEED_DB -> execute_nl2sql_flow() 로 SQL 생성
       -> restrict_sql_query_by_access() 로 권한별 WHERE 제한
       -> (새로 추가) 실제 DB에 쿼리 실행 (오류 시 자동 수정 & 재시도)
    4) 결과 문자열을 반환
    """
    try:
        logger.debug(
            f"[process_user_message] user_info={user_info}, access_level={access_level}"
        )
        logger.debug(f"[process_user_message] user_message={user_message}")

        # (Step 1) DB 필요 여부 분류
        db_need_result = classify_db_need(user_message)  # "NEED_DB" or "NO_DB"
        logger.debug(f"db_need_result={db_need_result}")

        # (Step 2) DB 조회 불필요 => 일반 대화
        if db_need_result == "NO_DB":
            response = chat_with_agent(user_message)
            return response

        # (Step 3-A) NL2SQL
        sql_query = execute_nl2sql_flow(user_message)
        logger.debug(f"raw sql_query={sql_query}")

        # (Step 3-B) 권한별 WHERE 제한
        final_sql = restrict_sql_query_by_access(sql_query, user_info, access_level)
        if not final_sql:
            return "해당 쿼리에 접근할 권한이 없습니다."

        logger.debug(f"final_sql={final_sql}")

        # (Step 3-C) 실제 DB 실행 + 오류 자동 수정
        #   - 아래 connection_params는 실제 환경에 맞춰 설정
        connection_params = {
            "host": "127.0.0.1",
            "user": "root",
            "password": "my_password",
            "database": "hrdatabase",
            "port": 3306,
        }

        # DB 스키마(테이블/컬럼) 정보 로드
        db_tables, db_columns = load_db_schema(connection_params, "hrdatabase")

        # 자동 수정 기능까지 포함된 실행
        run_result = run_sql_with_auto_fix(
            final_sql,
            connection_params,
            db_tables,
            db_columns,
            max_retries=1,  # 1~2회 정도 권장
        )
        return run_result

    except Exception as e:
        logger.error(
            "[process_user_message] Unexpected exception: %s", e, exc_info=True
        )
        return "죄송합니다, 내부 오류가 발생했습니다."
