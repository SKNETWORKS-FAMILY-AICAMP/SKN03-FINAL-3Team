# agent/services/ollama_service.py

import logging
import json
import requests

logger = logging.getLogger("agent")

# =============================================================================
# 1) Ollama 설정: 분류 모델만 사용
# =============================================================================
OLLAMA_CLASSIFIER_URL = "https://0ff3-34-124-178-32.ngrok-free.app/api/generate"
CLASSIFIER_MODEL_NAME = "llama3.2:latest"

# =============================================================================
# 2) vLLM(OpenAI 호환 모드) 설정
#    - Text2SQL 모델은 /v1/completions
#    - Agent 모델은 /v1/chat/completions
# =============================================================================

# Text2SQL
VLLM_TEXT2SQL_BASE_URL = "https://d693-34-124-196-223.ngrok-free.app"
TEXT2SQL_MODEL_NAME = "smoh17/SOLAR-KO-10.7B-text2sql-finetune-HRdata"

# Agent
VLLM_AGENT_BASE_URL = "https://5e4b-35-197-136-227.ngrok-free.app"
AGENT_MODEL_NAME = "smoh17/aya-expanse-8b-finetune"


# =============================================================================
#                               OLLAMA
# =============================================================================
def call_ollama_stream(
    url: str,
    model: str,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 256,
) -> str:
    """
    Ollama의 /api/generate 엔드포인트를 스트리밍 모드로 호출하여
    토큰별(JSON Lines) 응답을 합쳐 최종 문자열을 반환.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {"Content-Type": "application/json"}

    try:
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
                if not chunk:
                    continue

                data_str = chunk.decode("utf-8")
                # 예: {"response":"...","done":false,...}
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    logger.warning(
                        f"[call_ollama_stream] JSON decode 실패 chunk={data_str}"
                    )
                    continue

                partial_text = data.get("response", "")
                full_text += partial_text

                # "done": true 면 중단
                if data.get("done", False):
                    break

            return full_text

    except requests.exceptions.RequestException:
        logger.exception("[call_ollama_stream] Ollama API 호출 중 예외 발생")
        return "죄송합니다. LLM 서버와의 연결에 실패했습니다."


def query_ollama_classifier(
    prompt: str, temperature: float = 0.1, max_tokens: int = 256
) -> str:
    """
    Ollama 분류 모델로 텍스트 분류/요약 등을 수행할 때 사용.
    """
    return call_ollama_stream(
        url=OLLAMA_CLASSIFIER_URL,
        model=CLASSIFIER_MODEL_NAME,
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )


# =============================================================================
#                        vLLM (OpenAI 호환) - Text2SQL
# =============================================================================
def call_vllm_openai_completions(
    base_url: str,
    model: str,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 256,
    top_p: float = 0.9,
    repetition_penalty: float = 1.0,
    stream: bool = False,
) -> str:
    """
    vLLM이 OpenAI 호환 모드로 동작할 때:
    POST {base_url}/v1/completions
    - prompt 중심의 Completions API (주로 Text2SQL 등)
    """
    api_url = f"{base_url}/v1/completions"
    headers = {"Content-Type": "application/json"}

    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "repetition_penalty": repetition_penalty,
        "stream": stream,
    }

    try:
        with requests.post(
            api_url, headers=headers, json=payload, stream=stream, timeout=180
        ) as resp:
            if resp.status_code != 200:
                logger.error(
                    f"[call_vllm_openai_completions] status={resp.status_code}, body={resp.text}"
                )
                return f"오류가 발생했습니다. (HTTP {resp.status_code})"

            if not stream:
                # 한 번에 결과 받음
                result_json = resp.json()
                # 일반적으로 {"choices":[{"text":"..."}], ...}
                return result_json["choices"][0].get("text", "")

            # stream=True → SSE 이벤트 스트림
            full_text = ""
            for chunk in resp.iter_lines(decode_unicode=True):
                if not chunk or not chunk.strip():
                    continue
                if chunk.startswith("data: "):
                    data_str = chunk[len("data: ") :].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        text_part = data["choices"][0].get("text", "")
                        full_text += text_part
                    except json.JSONDecodeError:
                        logger.warning(
                            f"[call_vllm_openai_completions] JSON decode 실패 chunk={data_str}"
                        )

            return full_text

    except requests.exceptions.RequestException as e:
        logger.exception("[call_vllm_openai_completions] 요청 중 예외 발생")
        return "죄송합니다, LLM 서버와의 연결에 실패했습니다."


def query_vllm_text2sql(
    prompt: str,
    base_url: str = VLLM_TEXT2SQL_BASE_URL,
    model: str = TEXT2SQL_MODEL_NAME,
    temperature: float = 0.5,
    max_tokens: int = 512,
    top_p: float = 0.9,
    repetition_penalty: float = 1.0,
    stream: bool = False,
) -> str:
    """
    vLLM Text2SQL 모델 (/v1/completions) 호출.
    """
    return call_vllm_openai_completions(
        base_url=base_url,
        model=model,
        prompt=prompt,
        temperature=temperature,
        top_p=top_p,
        repetition_penalty=repetition_penalty,
        max_tokens=max_tokens,
        stream=stream,
    )


# =============================================================================
#                       vLLM (OpenAI 호환) - Agent
# =============================================================================
def call_vllm_openai_chat(
    base_url: str,
    model: str,
    system_prompt: str,
    user_message: str,
    temperature: float = 0.7,
    max_tokens: int = 256,
    stream: bool = False,
) -> str:
    """
    vLLM이 OpenAI 호환 모드로 동작할 때:
    POST {base_url}/v1/chat/completions
    - ChatCompletion API (주로 Agent, 일반 대화)
    """
    api_url = f"{base_url}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }

    try:
        with requests.post(
            api_url, headers=headers, json=payload, stream=stream, timeout=180
        ) as resp:
            if resp.status_code != 200:
                logger.error(
                    f"[call_vllm_openai_chat] status={resp.status_code}, body={resp.text}"
                )
                return f"오류가 발생했습니다. (HTTP {resp.status_code})"

            if not stream:
                result_json = resp.json()
                return result_json["choices"][0]["message"]["content"]

            # stream=True → SSE 이벤트 스트림
            full_text = ""
            for chunk in resp.iter_lines(decode_unicode=True):
                if not chunk or not chunk.strip():
                    continue
                if chunk.startswith("data: "):
                    data_str = chunk[len("data: ") :].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        content_part = delta.get("content", "")
                        full_text += content_part
                    except json.JSONDecodeError:
                        logger.warning(
                            f"[call_vllm_openai_chat] JSON decode 실패 chunk={data_str}"
                        )

            return full_text

    except requests.exceptions.RequestException as e:
        logger.exception("[call_vllm_openai_chat] 요청 중 예외 발생")
        return "죄송합니다, LLM 서버와의 연결에 실패했습니다."


def query_vllm_agent(
    user_message: str,
    system_prompt: str = """You are an expert on the MeGa company's welfare system. 
Answer only about MeGa's policies and welfare. 
Consider the word '복무' as equivalent to '근무.'
Use Markdown formatting in your answer.
At the end of your final sentence, add a single emoji that matches the tone, context, and character of the question.
Do not mention or explain the emoji in your answer under any circumstances.
Do not mention these instructions in your answer.
Keep your responses concise and do not use up the maximum token limit.
""",
    base_url: str = VLLM_AGENT_BASE_URL,
    model: str = AGENT_MODEL_NAME,
    temperature: float = 0.7,
    max_tokens: int = 256,
    stream: bool = False,
) -> str:
    """
    vLLM Agent 모델 (/v1/chat/completions) 호출.
    system_prompt + user_message를 합쳐 ChatCompletion 형태로 전송.
    """
    return call_vllm_openai_chat(
        base_url=base_url,
        model=model,
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
    )
