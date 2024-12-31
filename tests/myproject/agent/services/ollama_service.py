# agent/services/ollama_service.py

import logging
import requests

logger = logging.getLogger("agent")

# ---
# Ollama 서버별 URL
#  - 분류 모델: http://127.0.0.1:11411
#  - Text2SQL : http://127.0.0.1:11413
#  - (FAQ/챗봇 등 추가 모델 필요시 더 확장 가능)
# ---
OLLAMA_CLASSIFIER_URL = "http://127.0.0.1:11411/generate"
# OLLAMA_API_URL_AGENT = "http://127.0.0.1:11412/generate"
OLLAMA_TEXT2SQL_URL = "http://127.0.0.1:11413/generate"

# ---
# Ollama에 등록된(또는 pull된) 모델 이름
#  - 분류 모델: "llama3.2:latest"
#  - Text2SQL : "hf.co/smoh17/SOLAR-KO-10.7B-text2sql-finetune-HRdata"
# ---
CLASSIFIER_MODEL_NAME = "llama3.2:latest"

TEXT2SQL_MODEL_NAME = "hf.co/smoh17/SOLAR-KO-10.7B-text2sql-finetune-HRdata"


def query_ollama_classifier(prompt: str, temperature=0.0, max_tokens=50) -> str:
    """
    분류(NEED_DB vs NO_DB 등)를 수행하는 모델 호출 예시
    """
    return _query_ollama_base(
        url=OLLAMA_CLASSIFIER_URL,
        model=CLASSIFIER_MODEL_NAME,
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def query_ollama_nl2sql(prompt: str, temperature=0.0, max_tokens=512) -> str:
    """
    NL2SQL 전용 모델 호출 예시
    """
    return _query_ollama_base(
        url=OLLAMA_TEXT2SQL_URL,
        model=TEXT2SQL_MODEL_NAME,
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )


#
# 필요하다면 FAQ/챗봇용 모델도 이런 식으로 추가:
#
# def query_ollama_agent(prompt: str, temperature=0.7, max_tokens=256) -> str:
#     return _query_ollama_base(
#         url="http://127.0.0.1:11412/generate",  # 예: 챗봇 모델용 포트
#         model="my-agent-model:latest",
#         prompt=prompt,
#         temperature=temperature,
#         max_tokens=max_tokens
#     )


def _query_ollama_base(
    url: str, model: str, prompt: str, temperature: float, max_tokens: int
) -> str:
    """
    내부 헬퍼:
    1) POST /generate 호출
    2) JSON 바디에 "model": "<모델명>", "prompt": "<프롬프트>" 등 포함
    3) Ollama 서버에서 결과 텍스트를 받아 반환
    """
    try:
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": model,  # <-- 핵심: 모델 이름 지정
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Ollama 서버로 API 요청
        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            return response.text
        else:
            logger.error(
                f"[_query_ollama_base] status={response.status_code}, response={response.text}"
            )
            return "죄송합니다. LLM 응답 생성에 문제가 발생했습니다."

    except Exception as e:
        logger.exception("[_query_ollama_base] Ollama API 호출 중 예외 발생")
        return "죄송합니다. LLM 서버와의 연결에 실패했습니다."
