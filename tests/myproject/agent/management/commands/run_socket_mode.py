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
        web_client = WebClient(token=settings.SLACK_BOT_TOKEN)
        socket_mode_client = SocketModeClient(
            app_token=settings.SLACK_APP_TOKEN, web_client=web_client
        )

        # Socket Mode Client 인증 테스트 후 봇 유저 ID 캐싱(성능 최적화)
        auth_test = web_client.auth_test()
        bot_user_id = auth_test["user_id"]
        # logger.debug(f"Bot user ID: {bot_user_id}")

        # 이벤트 처리 함수 정의
        def process(client: SocketModeClient, req: SocketModeRequest):
            if req.type == "events_api":
                event = req.payload.get("event", {})
                event_id = req.payload.get("event_id", "")

                # logger.debug(f"Event received: event_id={event_id}, event={event}")

                # Slack 이벤트 확인 응답
                client.send_socket_mode_response(
                    SocketModeResponse(envelope_id=req.envelope_id)
                )

                # 이미 처리한 이벤트는 무시
                if event_id in processed_events:
                    logger.debug(f"Skipping already processed event_id={event_id}")
                    return
                processed_events.add(event_id)

                # 필터링: 봇 메시지나 서브타입 메시지는 무시
                if event.get("bot_id") or "subtype" in event:
                    logger.debug(
                        f"Ignoring bot or subtype message: event_id={event_id}"
                    )
                    return

                # 유저 메시지 처리
                user_message = event.get("text", "")
                channel_id = event.get("channel", "")
                user_id = event.get("user", "")
                parent_ts = event.get("ts")

                # logger.debug(f"Processing user message: user_id={user_id}, channel_id={channel_id}, text={user_message}")

                # 봇 언급(@bot_user_id)이 있는 메시지만 처리
                bot_mention = f"<@{bot_user_id}>"
                if bot_mention not in user_message:
                    logger.debug(
                        f"No bot mention found. Skipping message from user_id={user_id}"
                    )
                    return  # 봇 멘션이 없으면 무시

                # logger.debug("Bot mention found. Calling handle_slack_event.")
                # 실제 에이전트 로직 호출
                response_text = handle_slack_event(user_message, user_id, channel_id)
                # logger.debug(f"handle_slack_event returned response: {response_text}")

                # Slack에 응답 메시지 전송
                logger.debug(
                    f"Sending response to Slack: channel_id={channel_id}, text={response_text}"
                )
                client.web_client.chat_postMessage(
                    channel=channel_id, text=response_text, thread_ts=parent_ts
                )
                logger.debug("Response sent successfully.")

        # Socket Mode Client에 이벤트 리스너 등록
        socket_mode_client.socket_mode_request_listeners.append(process)
        socket_mode_client.connect()

        logger.info("Slack Socket Mode client started.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Socket Mode client stopped.")
