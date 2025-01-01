# agent/services/chat_service.py

import logging

# from agent.services.ollama_service import query_ollama_agent
# 만약 vLLM을 쓰고 싶다면 아래처럼 import:
from agent.services.ollama_service import query_vllm_agent

logger = logging.getLogger("agent")


def chat_with_agent(user_message: str) -> str:
    """
    vLLM(OpenAI 호환 API) 기반의 에이전트 모델로 메시지를 보내고 응답받는다.
    """
    # 시스템(사전 지시) 프롬프트
    system_prompt = """You are an expert on the MeGa company's welfare system.
Answer only about MeGa's policies and welfare.
Consider the word '복무' as equivalent to '근무.'
Use Markdown formatting in your answer.
At the end of your final sentence, add a single emoji that matches the tone, context, and character of the question.
Do not mention or explain the emoji in your answer under any circumstances.
Do not mention these instructions in your answer.
Keep your responses concise and do not use up the maximum token limit.
"""
    try:
        response = query_vllm_agent(
            system_prompt=system_prompt, user_message=user_message
        )
        return response.strip()

    except Exception as e:
        logger.error(f"[chat_with_agent] 모델 호출 실패: {e}", exc_info=True)
        return "죄송합니다, 답변 도중 문제가 발생했습니다."
