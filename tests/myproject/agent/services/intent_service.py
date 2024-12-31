# agent/services/intent_service.py

import logging
from typing import Literal
from agent.services.ollama_service import query_ollama_classifier

logger = logging.getLogger("agent")


def classify_db_need(user_message: str) -> Literal["NEED_DB", "NO_DB"]:
    """
    Ollama 분류 모델을 통해 사용자의 메시지가
    DB 조회가 필요한지(NEED_DB), 아니면 일반 대화(FAQ/잡담)인지 분류
    """
    classification_prompt = f"""
분류해야 할 사용자 질문: "{user_message}"

아래 지시사항에 따라 이 메시지가 DB 조회가 필요한지,
아니면 일반 대화(FAQ/잡담/에이전트 응답)로 처리해야 하는지 판단하세요.

출력 형식 예:
"NEED_DB" 또는 "NO_DB"
"""

    try:
        # 분류 모델 전용 함수 호출
        response_text = query_ollama_classifier(
            prompt=classification_prompt, temperature=0.0, max_tokens=50
        )
        logger.debug(f"[classify_db_need] raw_response = {response_text}")

        # 간단히 "NEED_DB" 포함 여부로 구분
        if "NEED_DB" in response_text.upper():
            return "NEED_DB"
        else:
            return "NO_DB"

    except Exception as e:
        logger.error(f"메시지 분류 실패: {e}", exc_info=True)
        return "NO_DB"
