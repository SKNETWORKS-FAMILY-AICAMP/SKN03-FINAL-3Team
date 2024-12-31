# agent/services/ollama_service.py

import logging
import requests

logger = logging.getLogger("agent")

# 모델별 URL
OLLAMA_API_URL_CLASSIFIER = "http://localhost:11411/generate"
OLLAMA_API_URL_AGENT = "http://localhost:11412/generate"
OLLAMA_API_URL_NL2SQL = "http://localhost:11413/generate"


def query_ollama_classifier(prompt: str, temperature=0.0, max_tokens=50) -> str:
    return _query_ollama_base(
        url=OLLAMA_API_URL_CLASSIFIER,
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def query_ollama_agent(prompt: str, temperature=0.7, max_tokens=256) -> str:
    return _query_ollama_base(
        url=OLLAMA_API_URL_AGENT,
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def query_ollama_nl2sql(prompt: str, temperature=0.0, max_tokens=512) -> str:
    return _query_ollama_base(
        url=OLLAMA_API_URL_NL2SQL,
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _query_ollama_base(
    url: str, prompt: str, temperature: float, max_tokens: int
) -> str:
    """
    실제 Ollama REST API 호출 로직.
    모델마다 URL만 달라지고 나머지는 동일하므로, 내부 헬퍼 함수로 통합.
    """
    try:
        headers = {"Content-Type": "application/json"}
        payload = {
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

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
