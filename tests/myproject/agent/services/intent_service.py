# agent/services/intent_service.py

import logging
from typing import Literal
from agent.services.ollama_service import query_ollama_classifier

logger = logging.getLogger("agent")


def classify_db_need(user_message: str) -> Literal["NEED_DB", "NO_DB"]:
    """
    Ollama 분류 모델을 통해 사용자의 메시지가
    DB 조회가 필요한지(NEED_DB), 아니면 일반 대화(FAQ/잡담)인지 분류
    """
    classification_prompt = f"""
You are a specialized classifier that must decide if a user query requires a database lookup ("NEED_DB") or if it can be addressed without querying any database ("NO_DB").

Below are the criteria and examples you must follow strictly. 
At the end, you must output exactly one of the following strings:
"NEED_DB"
or
"NO_DB"
(without quotes, and no additional explanation).

Criteria:

1) NEED_DB
   The user requests specific data typically stored in internal systems (HR, payroll, attendance logs, personal records, etc.).
   The query involves private or proprietary records that would require secure database retrieval (e.g., “급여명세서,” “연차 내역,” “인사팀 인원 상세정보”).

2) NO_DB
   The question can be handled without retrieving any personal or proprietary records from a database.
   Common examples: HR policy inquiries, general FAQs, casual conversation, or requests for information that do not involve personal data.

Guidelines:

- If the user’s request clearly demands personal or confidential information (logs, attendance, payroll, etc.), answer "NEED_DB".
- If the user’s request is general or does not require looking up any internal records, answer "NO_DB".
- If the user query is very short, unclear, or does not reference any form of personal or organizational data retrieval (e.g., "test", "hello", "안녕"), default to "NO_DB".
- Return only the strings "NEED_DB" or "NO_DB" (without quotes) and nothing else.


Examples:

1) 
Q: "내 이번 달 퇴근 시간 기록 좀 알려줘."
A: "NEED_DB"
(Explanation: Personal attendance data from HR system.)

2)
Q: "사내 조직도 좀 보여줄 수 있어?"
A: "NEED_DB"
(Explanation: Organizational charts are often stored in a proprietary database.)

3)
Q: "승진 기준이 어떻게 돼?"
A: "NO_DB"
(Explanation: Promotion criteria are general HR policy, not personal records.)

4)
Q: "내 지난주 연차 사용 내역 알려줘."
A: "NEED_DB"
(Explanation: Specific leave records are stored in the HR database.)

5)
Q: "사내 식당 메뉴가 궁금해."
A: "NO_DB"
(Explanation: Can be answered by a public or posted schedule, no DB needed.)

6)
Q: "나 이번 달 급여명세서 좀 볼 수 있을까?"
A: "NEED_DB"
(Explanation: Payroll records are securely stored in the database.)

7)
Q: "사내 복지 제도는 뭐가 있지?"
A: "NO_DB"
(Explanation: General HR policy, not personal data.)

8)
Q: "test"
A: "NO_DB"
(Explanation: Short, vague query that does not reference any data retrieval.)

Finally, consider that any query not explicitly requiring internal/private records is "NO_DB".
Answer with exactly "NEED_DB" or "NO_DB", nothing else.

"""

    try:
        # 분류 모델 전용 함수 호출
        response_text = query_ollama_classifier(
            prompt=classification_prompt, temperature=0.0, max_tokens=50
        )
        logger.debug(f"[classify_db_need] raw_response = {response_text}")

        # 간단히 "NEED_DB" 포함 여부로 구분
        if "NEED_DB" in response_text.upper():
            return "NEED_DB"
        else:
            return "NO_DB"

    except Exception as e:
        logger.error(f"메시지 분류 실패: {e}", exc_info=True)
        return "NO_DB"
