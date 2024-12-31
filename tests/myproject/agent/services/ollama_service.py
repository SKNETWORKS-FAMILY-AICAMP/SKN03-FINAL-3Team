# agent/services/ollama_service.py

import logging
import json
import requests

logger = logging.getLogger("agent")

# ---------------------------------------------------------------------
# Ollama 서버별 /api/generate 엔드포인트
# ---------------------------------------------------------------------
OLLAMA_CLASSIFIER_URL = "http://127.0.0.1:11411/api/generate"
OLLAMA_TEXT2SQL_URL = "http://127.0.0.1:11413/api/generate"
OLLAMA_AGENT_URL = "http://127.0.0.1:11412/api/generate"

# Ollama에 등록되어 있는 모델 이름(이미 pull되어 있어야 함)
CLASSIFIER_MODEL_NAME = "llama3.2:latest"
TEXT2SQL_MODEL_NAME = "hf.co/smoh17/SOLAR-KO-10.7B-text2sql-finetune-HRdata"
AGENT_MODEL_NAME = "my-agent-model:latest"


def call_ollama_stream(
    url: str, model: str, prompt: str, temperature: float, max_tokens: int
) -> str:
    """
    Ollama의 /api/generate 엔드포인트를 스트리밍 모드로 호출하여,
    토큰별로 전달되는 JSON chunk를 합쳐 최종 문자열을 반환한다.

    1) stream=True 로 요청
    2) r.iter_lines()로 partial JSON 수신
    3) `"response"` 필드를 누적, `"done": true` 시 종료
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "max_tokens": max_tokens,
        # "stream": False  # (만약 Ollama 버전이 지원한다면 비스트리밍 모드도 가능)
    }
    headers = {"Content-Type": "application/json"}

    try:
        # 스트리밍 모드
        with requests.post(
            url, json=payload, headers=headers, stream=True, timeout=180
        ) as resp:
            if resp.status_code != 200:
                logger.error(
                    f"[call_ollama_stream] status={resp.status_code}, body={resp.text}"
                )
                return f"오류가 발생했습니다. (HTTP {resp.status_code})"

            full_text = ""
            for chunk in resp.iter_lines():
                if chunk:
                    data_str = chunk.decode("utf-8")
                    # 예: {"model":"...","response":"...","done":false,...}
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        logger.warning(
                            f"[call_ollama_stream] JSON decode 실패 chunk={data_str}"
                        )
                        continue

                    # partial 토큰 추가
                    partial_text = data.get("response", "")
                    full_text += partial_text

                    # "done": true 면 중단
                    if data.get("done", False):
                        break
            return full_text

    except requests.exceptions.RequestException as e:
        logger.exception("[call_ollama_stream] Ollama API 호출 중 예외 발생")
        return "죄송합니다. LLM 서버와의 연결에 실패했습니다."


def query_ollama_classifier(
    prompt: str, temperature: float = 0.1, max_tokens: int = 256
) -> str:
    """
    예: Ollama의 분류 모델을 사용
    """
    return call_ollama_stream(
        url=OLLAMA_CLASSIFIER_URL,
        model=CLASSIFIER_MODEL_NAME,
        prompt=prompt,
        temperature=temperature,  # 여기서 인자 전달
        max_tokens=max_tokens,  # 여기서 인자 전달
    )


def query_ollama_nl2sql(
    prompt: str, temperature: float = 0.0, max_tokens: int = 512
) -> str:
    """
    DB 조회용 NL2SQL 모델
    """
    return call_ollama_stream(
        url=OLLAMA_TEXT2SQL_URL,
        model=TEXT2SQL_MODEL_NAME,
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def query_ollama_agent(
    prompt: str, temperature: float = 0.7, max_tokens: int = 256
) -> str:
    return call_ollama_stream(
        url=OLLAMA_AGENT_URL,
        model=AGENT_MODEL_NAME,
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )
