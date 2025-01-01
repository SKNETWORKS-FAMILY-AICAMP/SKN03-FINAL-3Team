# agent/services/query_service.py

from typing import Dict, Any
import sqlparse
import re
from sqlparse.sql import (
    Statement,
    TokenList,
    Where,
    Parenthesis,
    IdentifierList,
    Identifier,
    Comparison,
)
from sqlparse.tokens import Keyword, DML, Whitespace, Punctuation
import json
import logging
from agent.services.ollama_service import query_vllm_text2sql

logger = logging.getLogger("agent")


def execute_nl2sql_flow(
    user_message: str,
    schema_text: str = """hrdatabase_employee: employee_id (INT), employee_name (VARCHAR(100)), employee_level (VARCHAR(10)), employment_type (VARCHAR(10)), email (VARCHAR(100)), hire_date (DATE), home_ownership (VARCHAR(10)), child_age (VARCHAR(20)), gender (VARCHAR(10))
hrdatabase_attendancemanagement: employee_id (INT), total_late_days (INT), remaining_annual_leave (INT)
hrdatabase_attendancerecords: record_id (INT), employee_id (INT), work_date (DATE), is_absent (BOOLEAN), late_minutes (INT), actual_check_in_time (DATETIME), actual_check_out_time (DATETIME)
hrdatabase_welfarebenefitmanagement: employee_id (INT), childcare_used (BOOLEAN), company_housing (BOOLEAN), student_loan_used (BOOLEAN)
hrdatabase_teammanagement: team_id (INT), employee_id (INT), department (VARCHAR(100)), team_leader_tenure (INT)
""",
    max_new_tokens: int = 512,
    temperature: float = 0.5,
    top_p: float = 0.9,
    repetition_penalty: float = 1.0,
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
        generated_text = query_vllm_text2sql(
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
