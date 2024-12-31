from django.shortcuts import render
from django.conf import settings
import logging
from agent.services.agent_service import process_user_message


# 로깅 설정
logger = logging.getLogger(__name__)


def handle_slack_event(user_message, slack_id, channel_id):
    try:
        response_text = process_user_message(user_message, slack_id)
        # logger.debug(f"handle_slack_event - process_user_message response: {response_text}")
        return response_text
    except Exception as e:
        logger.exception("Exception in handle_slack_event")
        return "에러가 발생했습니다. 관리자에게 문의해주세요."
