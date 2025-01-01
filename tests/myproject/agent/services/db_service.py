import json
from django.utils import timezone
from agent.models import hrdatabase_chatbotconversations, hrdatabase_teammanagement

from agent.models import hrdatabase_teammanagement, hrdatabase_employee
from django.db import connection

def get_next_conversation_id():
    """
    데이터베이스에서 현재 최대 conversation_id 값을 확인하고 다음 ID를 반환합니다.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT MAX(CAST(conversation_id AS UNSIGNED)) FROM hrdatabase_chatbotconversations")
        max_id = cursor.fetchone()[0] or 0
        return str(int(max_id) + 1)

def get_team_id_by_user(user_id):
    """
    Slack user_id를 통해 팀 ID를 조회하는 함수.

    Parameters:
        - user_id (str): Slack user ID

    Returns:
        - str: 팀 ID
    """
    try:
        # 유저가 속한 팀 조회
        employee = hrdatabase_employee.objects.get(slack_id=user_id)
        team = hrdatabase_teammanagement.objects.get(employee_id=employee.employee_id)
        return team.team_id
    except hrdatabase_employee.DoesNotExist:
        raise ValueError(f"User ID '{user_id}' not found in hrdatabase_employee.")
    except hrdatabase_teammanagement.DoesNotExist:
        raise ValueError(f"Team for user ID '{user_id}' not found in hrdatabase_teammanagement.")
    

def save_conversation(question, answer, team_id_str, keyword_data=None):
    """
    대화 데이터를 저장하는 함수. conversation_id는 MySQL에서 자동 관리.
    """
    # 팀 ID 확인 및 조회
    team_obj = hrdatabase_teammanagement.objects.filter(team_id=team_id_str).first()
    if not team_obj:
        raise ValueError(f"Team ID '{team_id_str}' does not exist in the database.")

    # 키워드 데이터 처리
    keyword_str = json.dumps(keyword_data) if keyword_data else None

    # 대화 레코드 저장 (conversation_id는 MySQL에서 자동 증가)
    record = hrdatabase_chatbotconversations.objects.create(
        question=question,
        answer=answer,
        question_date=timezone.now().date(),
        team_id=team_obj,  # 외래키로 팀 객체 저장
        keyword=keyword_str,
    )
    return record