# management/commands/run_socket_mode.py

import time
import logging
import requests

from django.core.management.base import BaseCommand
from django.conf import settings

from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.web import WebClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.errors import SlackApiError

# [핵심] views.py 에서 handle_slack_event 임포트
from agent.views import handle_slack_event

logger = logging.getLogger("agent")
logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
console_handler = logging.StreamHandler()
logger.addHandler(console_handler)

processed_events = set()

def send_dm(user_id, message):
    # DM 보내기 헬퍼함수 (예시)
    headers = {
        'Authorization': f'Bearer {settings.SLACK_BOT_TOKEN}',
        'Content-type': 'application/json; charset=utf-8',
    }
    url = 'https://slack.com/api/chat.postMessage'
    payload = {
        'channel': user_id,
        'text': message,
    }
    response = requests.post(url, headers=headers, json=payload)
    ...

class Command(BaseCommand):
    help = "Run Slack Socket Mode client with extra debugging logs."

    def handle(self, *args, **options):
        logger.info("Initializing Slack WebClient with SLACK_BOT_TOKEN...")
        web_client = WebClient(token=settings.SLACK_BOT_TOKEN)

        try:
            auth_test_response = web_client.auth_test()
            logger.info(f"[startup] auth_test ok => {auth_test_response}")
        except SlackApiError as e:
            logger.error(f"[startup] auth_test failed => {e.response['error']}", exc_info=True)
            return

        logger.info("Initializing Slack SocketModeClient with SLACK_APP_TOKEN...")
        socket_mode_client = SocketModeClient(
            app_token=settings.SLACK_APP_TOKEN,
            web_client=web_client
        )

        def process(client: SocketModeClient, req: SocketModeRequest):
            logger.debug(f"[process] SocketModeRequest => type: {req.type}, payload: {req.payload}")

            if req.type == "events_api":
                event = req.payload.get("event", {})
                event_id = req.payload.get("event_id", "")

                # Ack
                client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))

                # 중복 이벤트 처리 방지
                if event_id in processed_events:
                    logger.debug(f"[process] Duplicate event_id={event_id}. Skipping this event.")
                    return
                processed_events.add(event_id)

                # 봇 메시지, subtype 등 무시
                bot_id = event.get("bot_id")
                subtype = event.get("subtype")
                if bot_id or subtype:
                    return

                event_type = event.get("type", "")
                channel_id = event.get("channel", "")
                user_id = event.get("user", "")
                user_message = event.get("text", "")
                event_ts = event.get("ts", None)
                channel_type = event.get("channel_type", "")

                # 1) app_mention 처리
                if event_type == "app_mention":
                    response_text = handle_slack_event(user_message, user_id, channel_id)
                    # 느낌표로 끝나면 DM
                    if user_message.strip().endswith("!"):
                        if response_text:
                            send_dm(user_id, response_text)
                    else:
                        if response_text:
                            try:
                                if channel_type == "channel":
                                    post_kwargs = {
                                        "channel": channel_id,
                                        "text": response_text,
                                        "thread_ts": event_ts,
                                    }
                                else:
                                    post_kwargs = {
                                        "channel": channel_id,
                                        "text": response_text,
                                    }
                                res = client.web_client.chat_postMessage(**post_kwargs)
                            except SlackApiError as e:
                                logger.error(f"Failed to send Slack channel message: {e.response['error']}", exc_info=True)

                # 2) 개인 DM 처리
                if event_type == "message" and channel_type == "im":
                    response_text = handle_slack_event(user_message, user_id, channel_id)
                    if response_text:
                        try:
                            post_kwargs = {
                                "channel": channel_id,
                                "text": response_text
                            }
                            res = client.web_client.chat_postMessage(**post_kwargs)
                        except SlackApiError as e:
                            logger.error(f"Failed to send DM: {e.response['error']}", exc_info=True)

        socket_mode_client.socket_mode_request_listeners.append(process)
        socket_mode_client.connect()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Socket Mode client stopped by KeyboardInterrupt.")
