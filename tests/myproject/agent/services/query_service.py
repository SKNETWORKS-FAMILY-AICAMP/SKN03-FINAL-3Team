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
    prompt = f"""Below is a concise summary of the database schema: {schema_text} Important: The 'is_absent' column exists only in the hrdatabase_attendancerecords table. Here are some example Q-SQL pairs: 1) Question: 전체 직원 목록과 직급, 이메일을 보여줘. SQL: SELECT employee_name, employee_level, email FROM hrdatabase_employee; 2) Question: 3개월 연속으로 결근이 발생한 직원은? SQL: WITH MonthlyAbsence AS (SELECT employee_id, DATE_FORMAT(work_date, '%Y-%m') AS month_yyyy_mm, SUM(CASE WHEN is_absent = TRUE THEN 1 ELSE 0 END) AS absence_count FROM hrdatabase_attendancerecords GROUP BY employee_id, DATE_FORMAT(work_date, '%Y-%m')) SELECT M1.employee_id FROM MonthlyAbsence M1 JOIN MonthlyAbsence M2 ON M1.employee_id = M2.employee_id AND DATE_ADD(STR_TO_DATE(M1.month_yyyy_mm, '%Y-%m'), INTERVAL -1 MONTH) = STR_TO_DATE(M2.month_yyyy_mm, '%Y-%m') JOIN MonthlyAbsence M3 ON M1.employee_id = M3.employee_id AND DATE_ADD(STR_TO_DATE(M1.month_yyyy_mm, '%Y-%m'), INTERVAL -2 MONTH) = STR_TO_DATE(M3.month_yyyy_mm, '%Y-%m') WHERE M1.absence_count > 0 AND M2.absence_count > 0 AND M3.absence_count > 0; 3) Question: 입사일이 5년 이상 된 직원 중, 복지 혜택을 전혀 이용하지 않는 직원은? SQL: SELECT E.employee_name, E.hire_date FROM hrdatabase_employee E JOIN hrdatabase_welfarebenefitmanagement W ON E.employee_id = W.employee_id WHERE TIMESTAMPDIFF(YEAR, E.hire_date, CURDATE()) >= 5 AND W.childcare_used = FALSE AND W.company_housing = FALSE; 4) Question: 연차가 남아있지만 결근한 직원들 보여줘. SQL: SELECT E.employee_name, A.remaining_annual_leave, R.work_date, R.is_absent FROM hrdatabase_employee E JOIN hrdatabase_attendancemanagement A ON E.employee_id = A.employee_id JOIN hrdatabase_attendancerecords R ON E.employee_id = R.employee_id WHERE A.remaining_annual_leave > 0 AND R.is_absent = TRUE; 5) Question: 자녀 나이가 7살인 경우 내년에 8살이 되므로 보육 혜택(또는 유아 대상 지원)이 종료될 직원 목록을 미리 알려줘. SQL: SELECT E.employee_name, E.child_age, W.childcare_used FROM hrdatabase_employee E JOIN hrdatabase_welfarebenefitmanagement W ON E.employee_id = W.employee_id WHERE E.child_age = 7 AND W.childcare_used = TRUE; IMPORTANT: UNDER NO CIRCUMSTANCES SHOULD YOU USE ROW_NUMBER() OR PARTITION. ALWAYS PREFER SIMPLE JOIN AND WHERE CONDITIONS. NO EXCEPTIONS. Now, You should convert the following user question into a SQL query. ### Question: {user_message} ### MYSQL:""".strip()

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
