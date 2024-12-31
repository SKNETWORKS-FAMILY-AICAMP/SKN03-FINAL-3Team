# agent/services/query_service.py

import logging
from agent.services.ollama_service import query_ollama_nl2sql
from agent.services.format_service import get_formatted_response

logger = logging.getLogger("agent")


def execute_nl2sql_flow(
    user_message: str,
    schema_text: str = "",
    max_new_tokens: int = 512,
    temperature: float = 0.0,
    # top_p: float = 0.9,
    # repetition_penalty: float = 1.0,
    **generate_kwargs,
) -> str:
    """
    사용자 질문(question_text)을 받아서, schema_text(옵션)과 함께
    (1) NL2SQL 프롬프트를 구성
    (2) query_ollama_nl2sql()로 호출
    (3) 최종 SQL 문자열을 리턴
    """

    # (A) prompt 구성
    prompt = f"""Below is a concise summary of the database schema: {schema_text}
IMPORTANT: UNDER NO CIRCUMSTANCES SHOULD YOU USE ROW_NUMBER() OR PARTITION. ALWAYS PREFER SIMPLE JOIN AND WHERE CONDITIONS. NO EXCEPTIONS.

Now, You should convert the following user question into a SQL query.

### Question:
{user_message}

### MYSQL:""".strip()

    # (B) 모델 호출 (ollama)
    try:
        # 모델에 prompt 전달
        generated_text = query_ollama_nl2sql(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_new_tokens,
            # top_p, repetition_penalty 등은 현재 query_ollama_nl2sql 파라미터에 따라 추가 가능
        )
        logger.debug(f"[generate_sql_v2] raw_text={generated_text}")
    except Exception as e:
        logger.error(
            f"[generate_sql_v2] query_ollama_nl2sql failed: {e}", exc_info=True
        )
        return ""

    # (C) SQL 부분만 추출
    if "### MYSQL:" in generated_text:
        generated_sql = generated_text.split("### MYSQL:")[-1].strip()
        return generated_sql

    return generated_text.strip()
