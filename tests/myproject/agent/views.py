from django.shortcuts import render


# Create your views here.
def handle_slack_event(user_message, user_id, channel_id):
    # 초기 구현: 단순 에코 응답
    return f"안녕하세요! 당신이 보낸 메시지: '{user_message}' 입니다."
