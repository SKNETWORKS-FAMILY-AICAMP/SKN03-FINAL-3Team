# agent/services/chat_service.py

import logging
from agent.services.ollama_service import query_ollama_agent


logger = logging.getLogger("agent")


def chat_with_agent(user_message: str) -> str:
    """
    Ollama(일반 채팅/FAQ 모델)로 메시지를 보내고 응답을 받아온다.
    """
    agent_prompt = f"""
사용자: {user_message}
시스템: 당신은 기업 내 챗봇 에이전트입니다. 친절하고 간결하게 답변하세요.
"""
    try:
        response = query_ollama_agent(
            prompt=agent_prompt,
            # 예: model_name="my-agent-model" (단일 서버에서 여러 모델 로드 시)
            temperature=0.7,
            max_tokens=256,
        )
        return response.strip()
    except Exception as e:
        logger.error(f"[chat_with_agent] 모델 호출 실패: {e}", exc_info=True)
        return "죄송합니다, 답변 도중 문제가 발생했습니다."
