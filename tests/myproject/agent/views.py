from django.shortcuts import render
# from agent.services.agent_service import process_user_message
from agent.services.role_service import get_user_role, get_access_level


def handle_slack_event(user_message, user_id, channel_id):
    # user_id는 Slack 상의 유저 ID (slack_id)라 가정
    user_info = get_user_role(user_id)  # DB에서 사용자 정보 조회

    if not user_info:
        return "해당 Slack 사용자를 찾을 수 없습니다."

    access_level = get_access_level(user_info)
    # 사용자 정보를 문자열 형태로 정리
    response_text = (
        f"사용자 정보:\n"
        f"이름: {user_info.get('name')}\n"
        f"직급: {user_info.get('rank_name')}\n"
        f"부서: {user_info.get('department_name')}\n"
        f"팀: {user_info.get('team_name')}\n"
        f"팀장여부: {'예' if user_info.get('team_leader') else '아니오'}\n"
        f"접근 수준: {access_level}\n"
    )

    return response_text
