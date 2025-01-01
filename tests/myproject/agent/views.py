from django.shortcuts import render
import logging

from agent.services.agent_service import process_user_message
from agent.services.role_service import get_user_role, get_access_level
from agent.services.db_service import save_conversation, get_team_id_by_user

logger = logging.getLogger("agent")

def handle_slack_event(user_message, user_id, channel_id, team_id_str=None):
    """
    Slack 이벤트를 처리하고 질문/답변을 저장하는 함수.
    """
    try:
        logger.debug(
            "[handle_slack_event] Entered with user_message=%s, user_id=%s, channel_id=%s, team_id_str=%s",
            user_message,
            user_id,
            channel_id,
            team_id_str,
        )

        # 유저 ID를 통해 팀 ID 조회
        if not team_id_str:
            try:
                team_id_str = get_team_id_by_user(user_id)
            except ValueError as e:
                logger.warning("[handle_slack_event] %s", e)
                return str(e)

        # 사용자 정보 및 접근 레벨 조회
        user_info = get_user_role(user_id)
        if not user_info:
            logger.warning("[handle_slack_event] user_info not found. user_id=%s", user_id)
            return "해당 Slack 사용자를 찾을 수 없습니다."

        access_level = get_access_level(user_info)
        logger.debug("[handle_slack_event] access_level=%s for user_id=%s", access_level, user_id)

        # 메인 로직 호출
        final_response = process_user_message(user_message, user_info, access_level)
        logger.debug("[handle_slack_event] final_response=%s", final_response)

        # 질문/답변 로그 저장
        try:
            conversation_obj = save_conversation(
                question=user_message,
                answer=final_response,
                team_id_str=team_id_str,
                keyword_data={
                    "channel_id": channel_id,
                    "access_level": access_level,
                },
            )
            logger.info(
                "[handle_slack_event] Saved conversation_id=%s",
                conversation_obj.conversation_id,
            )
        except Exception as e:
            logger.error("[handle_slack_event] Failed to save conversation: %s", e)
            return "대화 로그를 저장하는 중 오류가 발생했습니다."

        return final_response

    except Exception as e:
        logger.error("[handle_slack_event] Unexpected exception: %s", e, exc_info=True)
        return "죄송합니다, 내부 오류가 발생했습니다."
