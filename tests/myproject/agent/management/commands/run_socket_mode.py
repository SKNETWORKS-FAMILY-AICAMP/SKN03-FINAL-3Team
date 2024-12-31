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

# 기존 handle_slack_event 함수: 사용자 메시지를 처리해 답변을 생성하는 로직
# (세부 내용은 agent/views.py 안에 있다고 가정)
from agent.views import handle_slack_event

logger = logging.getLogger("agent")
logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
console_handler = logging.StreamHandler()
logger.addHandler(console_handler)

processed_events = set()


def get_user_id_by_email(email):
    headers = {
        "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
        "Content-type": "application/json; charset=utf-8",
    }
    url = f"https://slack.com/api/users.lookupByEmail?email={email}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data.get("ok"):
            return data["user"]["id"]
        else:
            logger.error(f"Error fetching user ID: {data.get('error')}")
    else:
        logger.error(f"HTTP Error while fetching user ID: {response.status_code}")
    return None


def send_dm(user_id, message):
    """
    DM을 보낼 때는 보통 chat.postMessage로 channel=user_id.
    """
    headers = {
        "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
        "Content-type": "application/json; charset=utf-8",
    }
    url = "https://slack.com/api/chat.postMessage"
    payload = {
        "channel": user_id,
        "text": message,
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        if data.get("ok"):
            logger.info("Message sent successfully.")
        else:
            logger.error(f"Error sending DM: {data.get('error')}")
    else:
        logger.error(f"HTTP Error while sending DM: {response.status_code}")


class Command(BaseCommand):
    help = "Run Slack Socket Mode client with extra debugging logs."

    def handle(self, *args, **options):
        logger.info("Initializing Slack WebClient with SLACK_BOT_TOKEN...")

        web_client = WebClient(token=settings.SLACK_BOT_TOKEN)

        try:
            auth_test_response = web_client.auth_test()
            logger.info(f"[startup] auth_test ok => {auth_test_response}")
        except SlackApiError as e:
            logger.error(
                f"[startup] auth_test failed => {e.response['error']}", exc_info=True
            )
            return

        logger.info("Initializing Slack SocketModeClient with SLACK_APP_TOKEN...")
        socket_mode_client = SocketModeClient(
            app_token=settings.SLACK_APP_TOKEN, web_client=web_client
        )

        def process(client: SocketModeClient, req: SocketModeRequest):
            logger.debug(
                f"[process] SocketModeRequest => type: {req.type}, payload: {req.payload}"
            )

            ################################################################
            # (0) Slash Command 처리 로직
            ################################################################
            if req.type == "slash_commands":
                command = req.payload.get("command")
                if command == "/관리자":
                    # 원하는 링크 주소 (예: 대시보드)
                    admin_link = "http://127.0.0.1:8000/"

                    try:
                        # Slash Command 응답 (ephemeral로 보낼 경우 chat_postEphemeral 사용)
                        client.web_client.chat_postEphemeral(
                            channel=req.payload["channel_id"],
                            user=req.payload["user_id"],
                            text=f"관리자 페이지 링크: {admin_link}",
                        )
                    except SlackApiError as e:
                        logger.error(
                            f"[slash_commands] Failed to respond: {e.response['error']}",
                            exc_info=True,
                        )

                # Slash Command 받은 뒤에는 반드시 ack 필요
                client.send_socket_mode_response(
                    SocketModeResponse(envelope_id=req.envelope_id)
                )
                return

            ################################################################
            # (1) 이벤트 타입: events_api
            ################################################################
            if req.type == "events_api":
                event = req.payload.get("event", {})
                event_id = req.payload.get("event_id", "")
                client.send_socket_mode_response(
                    SocketModeResponse(envelope_id=req.envelope_id)
                )

                # 이미 처리한 event_id면 무시
                if event_id in processed_events:
                    logger.debug(
                        f"[process] Duplicate event_id={event_id}. Skipping this event."
                    )
                    return
                processed_events.add(event_id)

                bot_id = event.get("bot_id")
                subtype = event.get("subtype")
                # 봇 자신이 보낸 메시지, 또는 subtype이 있는 이벤트(파일 업로드 등)는 무시
                if bot_id or subtype:
                    return

                event_type = event.get("type", "")
                channel_id = event.get("channel", "")
                user_id = event.get("user", "")
                user_message = event.get("text", "")
                event_ts = event.get("ts", None)
                channel_type = event.get("channel_type", "")

                ################################################################
                # (1) @앱 맨션을 받았을 때 (예: 채널)
                ################################################################
                if event_type == "app_mention":
                    logger.debug(
                        f"[process] Mention received: user_id={user_id}, text={user_message}"
                    )

                    # 1) 메시지가 '!'로 끝나면 DM 로직
                    if user_message.strip().endswith("!"):
                        # handle_slack_event로 답변 생성
                        response_text = handle_slack_event(
                            user_message, user_id, channel_id
                        )

                        if response_text:
                            # DM 전송
                            send_dm(user_id, response_text)

                        # 채널에는 일반 메시지로 "DM으로 답변을 보냈습니다."
                        try:
                            client.web_client.chat_postMessage(
                                channel=channel_id, text="DM으로 답변을 보냈습니다."
                            )
                        except SlackApiError as e:
                            logger.error(
                                f"[process] Failed to notify channel: {e.response['error']}",
                                exc_info=True,
                            )

                    # 2) 메시지가 '!'로 끝나지 않을 때 → 스레드 답변
                    else:
                        response_text = handle_slack_event(
                            user_message, user_id, channel_id
                        )
                        if response_text:
                            try:
                                # "로딩 중..." 메시지 없이 바로 스레드에 답변
                                client.web_client.chat_postMessage(
                                    channel=channel_id,
                                    text=response_text,
                                    thread_ts=event_ts,
                                )
                            except SlackApiError as e:
                                logger.error(
                                    f"[process] Failed to send Slack channel message: {e.response['error']}",
                                    exc_info=True,
                                )

                ################################################################
                # (2) DM(1:1 대화) 로직
                ################################################################
                elif event_type == "message" and channel_type == "im":
                    logger.debug(
                        f"[process] DM received: user={user_id}, text={user_message}"
                    )

                    # DM에서는 기존 로직 그대로 "로딩 중" -> 최종 답변 업데이트
                    try:
                        loading_res = client.web_client.chat_postMessage(
                            channel=channel_id, text="적합한 자료를 모으는 중..."
                        )
                        loading_ts = loading_res["ts"]
                    except SlackApiError as e:
                        logger.error(
                            f"[process] Failed to send loading (DM) message: {e.response['error']}",
                            exc_info=True,
                        )
                        return

                    # 최종 답변 생성
                    response_text = handle_slack_event(
                        user_message, user_id, channel_id
                    )
                    if response_text:
                        try:
                            client.web_client.chat_update(
                                channel=channel_id, ts=loading_ts, text=response_text
                            )
                        except SlackApiError as e:
                            logger.error(
                                f"[process] Failed to send Slack DM: {e.response['error']}",
                                exc_info=True,
                            )

                # 그 외 이벤트는 무시 (채널 일반 메시지, 파일 업로드 등)

        # SocketModeClient에 이벤트 리스너 등록
        socket_mode_client.socket_mode_request_listeners.append(process)
        socket_mode_client.connect()

        # 메인 루프 유지
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Socket Mode client stopped by KeyboardInterrupt.")
