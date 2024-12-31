# agent/services/agent_service.py

import logging
from typing import Dict, Any
import re

from agent.services.intent_service import classify_db_need
from agent.services.chat_service import chat_with_agent
from agent.services.query_service import execute_nl2sql_flow

logger = logging.getLogger("agent")


def process_user_message(
    user_message: str, user_info: Dict[str, Any], access_level: str
) -> str:
    """
    1) Ollama 분류 모델로 'DB가 필요한 질문인지' 판별 (classify_db_need)
    2) DB 조회가 필요 없다면 => chat_with_agent() 호출
    3) DB 조회가 필요하다면 => execute_nl2sql_flow() 호출
    4) 최종 결과 문자열을 반환
    """
    try:
        user_name = user_info.get("name")
        rank_name = user_info.get("rank_name")

        logger.debug(
            f"[process_user_message] (Step 0) user={user_name}, rank={rank_name}, access_level={access_level}"
        )
        logger.debug(f"[process_user_message] (Step 0) user_message={user_message}")

        # (Step 1) 의도 분류
        logger.info("[process_user_message] (Step 1) Classifying whether DB is needed.")
        db_need_result = classify_db_need(user_message)  # "NEED_DB" or "NO_DB"
        logger.debug(f"[process_user_message] (Step 1) db_need_result={db_need_result}")

        # (Step 2) DB 조회 불필요 => 일반(FAQ/잡담) 대화
        if db_need_result == "NO_DB":
            logger.info(
                "[process_user_message] (Step 2) Result=NO_DB => chat_with_agent()"
            )
            response = chat_with_agent(user_message)
            logger.debug(
                f"[process_user_message] (Step 2) chat_with_agent response={response}"
            )
            return response

        # (Step 3) DB 조회가 필요한 경우 => nl2sql flow
        logger.info(
            "[process_user_message] (Step 3) Result=NEED_DB => execute_nl2sql_flow()"
        )

        response = execute_nl2sql_flow(
            user_message,
            user_info,
            access_level,
            _extract_sql_from_ollama,
            _is_sql_permitted,
        )
        logger.debug(
            f"[process_user_message] (Step 3) execute_nl2sql_flow response={response}"
        )
        return response

    except Exception as e:
        logger.error(
            "[process_user_message] Unexpected exception: %s", e, exc_info=True
        )
        # 사용자에게 노출할 오류 메시지(개발용/운영용 구분해서 변경 가능)
        return "죄송합니다, 내부 오류가 발생했습니다."


#
# 아래 2개 헬퍼 함수는 agent_service.py 내부에 두어도 되고, 별도 파일로 분리해도 됩니다.
#


def _extract_sql_from_ollama(nl2sql_response: str) -> str:
    """
    Ollama nl2sql 모델 응답에서 SQL 문을 추출하는 예시.
    실제로는 JSON 응답, 다른 구분자 등을 쓸 수 있음.
    """
    import re

    pattern = r"```sql\s*(.*?)\s*```"
    match = re.search(pattern, nl2sql_response, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # fallback
    return nl2sql_response.strip()


def _is_sql_permitted(sql_query: str, access_level: str) -> bool:
    """
    단순 예시: admin 아닌 경우 특정 테이블 차단
    """
    restricted_tables = ["financial", "executives"]
    if access_level != "admin":
        for tbl in restricted_tables:
            if tbl in sql_query.lower():
                return False
    return True