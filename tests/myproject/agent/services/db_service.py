import json
from django.utils import timezone
from agent.models import hrdatabase_chatbotconversations, hrdatabase_teammanagement


def save_conversation(question, answer, team_id_str, keyword_data=None):
    """
    사용자의 질문, 대답, 팀 ID, 날짜, 키워드 데이터를 저장하는 함수.

    Parameters:
        - question (str): 사용자가 입력한 질문
        - answer (str): 응답 내용
        - team_id_str (str): 팀 ID 문자열
        - keyword_data (dict, optional): 추가 키워드 데이터 (JSON 형태로 저장)

    Returns:
        - hrdatabase_chatbotconversations 객체: 저장된 레코드 객체
    """
    # 팀 ID 확인 및 조회
    try:
        team_obj = hrdatabase_teammanagement.objects.get(team_id=team_id_str)
    except hrdatabase_teammanagement.DoesNotExist:
        raise ValueError(f"Team ID '{team_id_str}' does not exist in the database.")

    # 키워드 데이터 처리
    keyword_str = json.dumps(keyword_data) if keyword_data else None

    # 대화 레코드 저장
    record = hrdatabase_chatbotconversations.objects.create(
        question=question,
        answer=answer,
        question_date=timezone.now().date(),
        team_id=team_obj,  # 외래키로 팀 객체 저장
        keyword=keyword_str
    )
    return record
