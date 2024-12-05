# slack_app.py

import os
import sys
import logging
import requests
import pickle
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from openai import OpenAI
from PyPDF2 import PdfReader
import numpy as np
import tiktoken

# =========================
# 1. 환경 설정 및 초기화
# =========================

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("bot.log")],
)
logger = logging.getLogger(__name__)

# Slack Bolt 앱 초기화
app = App(token=os.getenv("SLACK_BOT_TOKEN"))

# OpenAI 클라이언트 초기화
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

# 봇 사용자 ID 가져오기
try:
    bot_user_id = app.client.auth_test()["user_id"]
except Exception as e:
    logger.error(f"봇 사용자 ID 가져오기 실패: {e}")
    sys.exit(1)

# =========================
# 2. 임베딩 및 문서 관리
# =========================

# 임베딩 데이터를 저장할 리스트
embeddings_data = []


# 임베딩 데이터를 파일에서 로드하는 함수
def load_embeddings():
    global embeddings_data
    if os.path.exists("embeddings.pkl"):
        with open("embeddings.pkl", "rb") as f:
            embeddings_data = pickle.load(f)
        logger.info("임베딩 데이터 로드 완료.")
    else:
        embeddings_data = []
        logger.info("임베딩 데이터 파일이 존재하지 않습니다. 새로 생성됩니다.")


# 임베딩 데이터를 저장하는 함수
def save_embeddings():
    with open("embeddings.pkl", "wb") as f:
        pickle.dump(embeddings_data, f)
    logger.info("임베딩 데이터 저장 완료.")


# 텍스트를 토큰 수에 기반하여 분할하는 함수
def split_text(text, max_tokens=8000):
    tokenizer = tiktoken.get_encoding("cl100k_base")
    tokens = tokenizer.encode(text)
    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i : i + max_tokens]
        chunk_text = tokenizer.decode(chunk_tokens)
        chunks.append(chunk_text)
    return chunks


# 규정 데이터를 저장하는 함수 (임베딩 포함)
def save_regulation(title, content):
    # 텍스트를 청크로 분할
    chunks = split_text(content, max_tokens=8000)
    for idx, chunk in enumerate(chunks):
        # 청크별로 임베딩 생성
        embedding = get_embedding(chunk)
        if embedding is None:
            logger.error(
                f"임베딩 생성에 실패하여 규정 '{title}'의 청크 {idx+1}을(를) 저장하지 못했습니다."
            )
            continue
        # 임베딩 데이터 추가
        embeddings_data.append(
            {
                "title": f"{title} - 청크 {idx+1}",
                "content": chunk,
                "embedding": embedding,
            }
        )
    # 임베딩 데이터 파일로 저장
    save_embeddings()
    logger.info(
        f"규정 '{title}'이 저장되었습니다. 총 {len(chunks)}개의 청크로 분할되었습니다."
    )


# 텍스트 추출 함수 (PDF 파일에서 텍스트 추출)
def extract_text_from_pdf(file_path):
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                text += extracted_text
    except Exception as e:
        logger.error(f"PDF 텍스트 추출 실패: {e}")
    return text


# 임베딩 생성 함수
def get_embedding(text, model="text-embedding-ada-002"):
    try:
        response = client.embeddings.create(input=text, model=model)
        embedding = response.data[0].embedding  # 수정된 부분
        return embedding
    except Exception as e:
        logger.error(f"임베딩 생성 실패: {e}")
        return None


# 코사인 유사도 계산 함수
def cosine_similarity(vec1, vec2):
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
        return 0
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


# 관련 문서 검색 함수
def find_relevant_documents(question, top_k=3):
    load_embeddings()
    if not embeddings_data:
        logger.warning("임베딩 데이터가 비어 있습니다.")
        return []

    # 질문의 임베딩 생성
    question_embedding = get_embedding(question)
    if not question_embedding:
        return []

    # 각 문서와의 코사인 유사도 계산
    for data in embeddings_data:
        data["similarity"] = cosine_similarity(question_embedding, data["embedding"])

    # 유사도에 따라 정렬하여 상위 top_k 문서 선택
    sorted_data = sorted(embeddings_data, key=lambda x: x["similarity"], reverse=True)
    return sorted_data[:top_k]


# =========================
# 3. OpenAI 응답 생성
# =========================


def generate_response(context, user_question):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # 또는 "gpt-4"
            messages=[
                {
                    "role": "system",
                    "content": f"당신은 회사 규정에 대해 답변해주는 어시스턴트입니다. 다음은 회사 규정의 일부입니다:\n{context}",
                },
                {"role": "user", "content": user_question},
            ],
            max_tokens=300,
            temperature=0.5,
        )
        ai_response = response.choices[0].message.content.strip()  # 수정된 부분
        return ai_response
    except Exception as e:
        logger.error(f"OpenAI 응답 생성 실패: {e}")
        return "죄송합니다. 답변을 생성하는 중 오류가 발생했습니다."


# =========================
# 4. 이벤트 핸들러
# =========================


# 앱 멘션 이벤트 핸들러 (봇이 멘션되었을 때만 응답)
@app.event("app_mention")
def handle_app_mention_events(event, say):
    try:
        user_message = event.get("text", "")
        user_id = event.get("user")

        logger.info(f"앱 멘션 메시지 수신: {user_message}")

        # 봇 멘션 제거
        user_message = user_message.replace(f"<@{bot_user_id}>", "").strip()

        if not user_message:
            say("안녕하세요! 규정에 대해 질문이 있으시면 말씀해 주세요.")
            return

        # 관련 문서 검색
        relevant_docs = find_relevant_documents(user_message)

        if not relevant_docs:
            say("죄송합니다. 관련된 규정을 찾을 수 없습니다.")
            return

        # 관련 문서의 내용을 결합
        context = "\n\n".join(
            [f"제목: {doc['title']}\n내용: {doc['content']}" for doc in relevant_docs]
        )

        # OpenAI API 호출하여 응답 생성
        ai_response = generate_response(context, user_message)
        say(ai_response)
        logger.info("앱 멘션 응답 전송 완료.")

    except Exception as e:
        logger.error(f"오류 발생: {e}")
        say("죄송합니다. 답변을 생성하는 중 오류가 발생했습니다.")


# 메시지 이벤트 핸들러 (멘션된 메시지에서 파일 공유 처리)
@app.event("message")
def handle_message_events(event, say):
    try:
        # 메시지에서 subtype과 text를 가져옴
        subtype = event.get("subtype")
        text = event.get("text", "")
        user_id = event.get("user")

        # 메시지에 봇 멘션이 포함되어 있는지 확인
        if f"<@{bot_user_id}>" in text:
            # 파일 공유인지 확인
            if subtype == "file_share":
                files = event.get("files")
                if not files:
                    logger.warning("파일 정보가 없습니다.")
                    say(text="파일 정보가 없습니다.")
                    return

                for file_info in files:
                    file_id = file_info["id"]
                    file_name = file_info["name"]
                    file_url = file_info["url_private_download"]

                    logger.info(f"파일 수신: {file_name}")

                    # 파일 다운로드
                    headers = {
                        "Authorization": f"Bearer {os.getenv('SLACK_BOT_TOKEN')}"
                    }
                    response = requests.get(file_url, headers=headers)

                    if response.status_code != 200:
                        logger.error(
                            f"파일 다운로드 실패: 상태 코드 {response.status_code}"
                        )
                        say(text="파일 다운로드에 실패했습니다.")
                        return

                    # 파일 저장
                    os.makedirs("uploaded_files", exist_ok=True)
                    local_file_path = os.path.join("uploaded_files", file_name)
                    with open(local_file_path, "wb") as f:
                        f.write(response.content)

                    logger.info(f"파일 저장 완료: {local_file_path}")

                    # 파일에서 텍스트 추출 (예: PDF 파일)
                    extracted_text = extract_text_from_pdf(local_file_path)
                    if not extracted_text:
                        say(text=f"파일 '{file_name}'에서 텍스트를 추출할 수 없습니다.")
                        continue

                    # 규정 데이터베이스에 저장 (임베딩 포함)
                    save_regulation(file_name, extracted_text)

                    # 사용자에게 파일 처리 완료 메시지
                    say(text=f"파일 '{file_name}'이 성공적으로 처리되었습니다.")

            else:
                # 봇 멘션이 포함된 다른 유형의 메시지는 무시하거나 처리할 수 있습니다.
                pass

        else:
            # 봇 멘션이 없는 메시지는 무시
            pass

    except Exception as e:
        logger.error(f"파일 처리 중 오류 발생: {e}")
        say("죄송합니다. 파일을 처리하는 중 오류가 발생했습니다.")


# =========================
# 5. 메인 실행
# =========================

if __name__ == "__main__":
    logger.info("Slack 봇 시작됨.")
    handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    handler.start()
