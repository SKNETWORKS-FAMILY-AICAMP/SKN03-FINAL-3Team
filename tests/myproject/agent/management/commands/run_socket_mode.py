from django.core.management.base import BaseCommand
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.web import WebClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from django.conf import settings
from agent.views import handle_slack_event
import time
import logging

# 로깅 설정
logger = logging.getLogger("agent")
logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
console_handler = logging.StreamHandler()
logger.addHandler(console_handler)

# 처리된 이벤트 ID 저장소
processed_events = set()


class Command(BaseCommand):
    help = "Run Slack Socket Mode client"

    def handle(self, *args, **options):
        # Slack WebClient와 SocketModeClient 초기화
        web_client = WebClient(token=settings.SLACK_BOT_TOKEN)
        socket_mode_client = SocketModeClient(
            app_token=settings.SLACK_APP_TOKEN, web_client=web_client
        )

        # 이벤트 처리 함수 정의
        def process(client: SocketModeClient, req: SocketModeRequest):
            if req.type == "events_api":
                event = req.payload.get("event", {})
                event_id = req.payload.get("event_id", "")

                # Slack 이벤트 확인 응답
                client.send_socket_mode_response(
                    SocketModeResponse(envelope_id=req.envelope_id)
                )

                # 이미 처리한 이벤트는 무시
                if event_id in processed_events:
                    return
                processed_events.add(event_id)

                # 필터링: 봇 메시지나 서브타입 메시지는 무시
                if event.get("bot_id") or "subtype" in event:
                    return

                # 유저 메시지 처리
                user_message = event.get("text", "")
                channel_id = event.get("channel", "")
                user_id = event.get("user", "")

                # 간단한 응답 처리
                response_text = (
                    f"안녕하세요! 당신이 보낸 메시지: '{user_message}' 입니다."
                )
                client.web_client.chat_postMessage(
                    channel=channel_id, text=response_text
                )

        # Socket Mode Client에 이벤트 리스너 등록
        socket_mode_client.socket_mode_request_listeners.append(process)

        # Socket Mode Client 시작
        socket_mode_client.connect()

        logger.info("Slack Socket Mode client started.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Socket Mode client stopped.")
