from django.shortcuts import render
import logging

from agent.services.agent_service import process_user_message
from agent.services.role_service import get_user_role, get_access_level

logger = logging.getLogger("agent")


def handle_slack_event(user_message, user_id, channel_id):
    """
    Slack의 user_id(=slack_id)로 DB의 사용자 정보를 조회하고,
    agent_service.py의 process_user_message()로
    SQL/LLM/Ollama 연동 로직을 수행한 뒤,
    최종적으로 Slack에 보낼 응답 문자열을 반환합니다.
    """

    try:
        logger.debug(
            "[handle_slack_event] Entered with user_message=%s, user_id=%s, channel_id=%s",
            user_message,
            user_id,
            channel_id,
        )

        # 1) DB에서 사용자 정보 조회
        user_info = get_user_role(user_id)
        if not user_info:
            logger.warning(
                "[handle_slack_event] user_info not found. user_id=%s", user_id
            )
            return "해당 Slack 사용자를 찾을 수 없습니다."

        # 2) 접근 레벨 조회
        access_level = get_access_level(user_info)
        logger.debug(
            "[handle_slack_event] access_level=%s for user_id=%s", access_level, user_id
        )

        # 3) 실제 에이전트 메인 로직 호출 (intent 분류, 권한 체크, SQL/LLM 질의 등)
        logger.info("[handle_slack_event] Calling process_user_message()...")
        final_response = process_user_message(user_message, user_info, access_level)

        logger.debug("[handle_slack_event] final_response=%s", final_response)
        return final_response

    except Exception as e:
        logger.error("[handle_slack_event] Unexpected exception: %s", e, exc_info=True)
        # 사용자에게 노출할 오류 메시지
        return "죄송합니다, 내부 오류가 발생했습니다."