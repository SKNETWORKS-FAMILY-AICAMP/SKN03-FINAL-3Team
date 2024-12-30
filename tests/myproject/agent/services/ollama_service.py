import logging
import requests

logger = logging.getLogger("agent")

OLLAMA_API_URL = "http://localhost:11411/generate"

def query_ollama(prompt: str, temperature=0.7, max_tokens=256) -> str:
    """
    Ollama REST API에 prompt를 전달하고, 결과 텍스트를 반환하는 함수.
    Ollama의 실제 응답 형식(스트리밍, JSON 등)에 따라 parse를 조정해야 할 수 있음.
    """
    try:
        headers = {"Content-Type": "application/json"}
        payload = {
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        response = requests.post(OLLAMA_API_URL, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            return response.text  # 단순 텍스트로 가정
        else:
            logger.error(f"[query_ollama] status={response.status_code}, response={response.text}")
            return "죄송합니다. LLM 응답 생성에 문제가 발생했습니다."
    except Exception as e:
        logger.exception("[query_ollama] Ollama API 호출 중 예외 발생")
        return "죄송합니다. LLM 서버와의 연결에 실패했습니다."
