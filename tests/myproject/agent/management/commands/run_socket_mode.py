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

from agent.views import handle_slack_event

logger = logging.getLogger("agent")
logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
console_handler = logging.StreamHandler()
logger.addHandler(console_handler)

processed_events = set()


def get_user_id_by_email(email):
    headers = {
        'Authorization': f'Bearer {settings.SLACK_BOT_TOKEN}',
        'Content-type': 'application/json; charset=utf-8',
    }
    url = f'https://slack.com/api/users.lookupByEmail?email={email}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data.get('ok'):
            return data['user']['id']
        else:
            logger.error(f"Error fetching user ID: {data.get('error')}")
    else:
        logger.error(f"HTTP Error while fetching user ID: {response.status_code}")
    return None


def send_dm(user_id, message):
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
    if response.status_code == 200:
        data = response.json()
        if data.get('ok'):
            logger.info("Message sent successfully.")
        else:
            logger.error(f"Error sending message: {data.get('error')}")
    else:
        logger.error(f"HTTP Error while sending message: {response.status_code}")


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
                client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))

                if event_id in processed_events:
                    logger.debug(f"[process] Duplicate event_id={event_id}. Skipping this event.")
                    return
                processed_events.add(event_id)

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

                if event_type == "app_mention":
                    logger.debug(f"[process] Mention received: user_id={user_id}, text={user_message}")

                    # 특정 조건 확인: 메시지가 "!"로 끝나는지
                    if user_message.strip().endswith("!"):
                        logger.debug("[process] Message ends with '!' => Sending DM.")
                        response_text = handle_slack_event(user_message, user_id, channel_id)
                        if response_text:
                            send_dm(user_id, response_text)
                    else:
                        logger.debug("[process] Message does not end with '!' => Replying in thread.")
                        response_text = handle_slack_event(user_message, user_id, channel_id)
                        if response_text:
                            try:
                                post_kwargs = {
                                    "channel": channel_id,
                                    "text": response_text,
                                    "thread_ts": event_ts,  # 스레드 형식으로 답변
                                }
                                res = client.web_client.chat_postMessage(**post_kwargs)
                                logger.debug(f"[process] Channel thread response => {res}")
                            except SlackApiError as e:
                                logger.error(f"[process] Failed to send Slack channel message: {e.response['error']}", exc_info=True)

        socket_mode_client.socket_mode_request_listeners.append(process)
        socket_mode_client.connect()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Socket Mode client stopped by KeyboardInterrupt.")
