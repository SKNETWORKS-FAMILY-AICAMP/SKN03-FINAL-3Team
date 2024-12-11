from django.shortcuts import render
from agent.services.agent_service import process_user_message


def handle_slack_event(user_message, user_id, channel_id):
    # 전체 파이프라인 실행
    # user_message -> 의도분류 -> CoT -> SQL -> 결과 포맷팅
    response_text = process_user_message(user_message, user_id)
    return response_text
