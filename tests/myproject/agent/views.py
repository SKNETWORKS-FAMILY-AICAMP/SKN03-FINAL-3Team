from django.shortcuts import render
from agent.services.agent_service import process_user_message
from agent.services.role_service import get_user_role, get_access_level

def handle_slack_event(user_message, user_id, channel_id):
    """
    Slack의 user_id(=slack_id)로 DB의 사용자 정보를 조회하고,
    추가로 agent_service.py의 process_user_message()로
    SQL/LLM/Ollama 연동 로직을 수행한 뒤,
    최종적으로 Slack에 보낼 응답 문자열을 반환합니다.
    """

    # 1) DB에서 사용자 정보 조회
    user_info = get_user_role(user_id)  # slack_id -> user_info
    if not user_info:
        return "해당 Slack 사용자를 찾을 수 없습니다."

    # 2) 기존처럼 접근 레벨도 조회
    access_level = get_access_level(user_info)

    # 3) 실제 에이전트 메인 로직 호출
    #    (intent 분류, 권한 체크, SQL/LLM 질의 등)
    final_response = process_user_message(user_message, user_id)

    # 4) 기존처럼 사용자 정보를 문자열 형태로 만들어둠
    user_info_str = (
        f"사용자 정보:\n"
        f"이름: {user_info.get('name')}\n"
        f"직급: {user_info.get('rank_name')}\n"
        f"부서: {user_info.get('department_name')}\n"
        f"팀: {user_info.get('team_name')}\n"
        f"팀장여부: {'예' if user_info.get('team_leader') else '아니오'}\n"
        f"접근 수준: {access_level}\n"
    )

    # 5) 최종적으로 "사용자 정보" + "process_user_message()의 응답"을 합쳐서 반환
    #    (원한다면 합치지 않고 process_user_message() 결과만 주거나, 
    #     원하는 형태로 가공 가능)
    combined_response = user_info_str + "\n" + final_response

    return combined_response
