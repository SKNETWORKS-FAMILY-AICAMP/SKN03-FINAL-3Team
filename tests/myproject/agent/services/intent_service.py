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
User query to classify: "{user_message}"

You must decide if the user query requires access to a database ("NEED_DB") or if it can be answered without database access ("NO_DB"). 

Criteria:
1. **NEED_DB**  
   - The user is requesting specific data that is typically stored and managed in internal databases or HR systems (e.g., attendance logs, payroll details, personal leave records).
   - The query explicitly refers to private or proprietary data (e.g., “퇴근 시간 기록,” “급여명세서 내역,” “연차 사용 현황”).
   - The user’s request implies a need to look up structured records.

2. **NO_DB**  
   - The request can be handled without querying a database, such as providing HR policies, general FAQs about the company, or casual conversation.
   - The user is asking for general guidance, a company-wide policy, or information that does not rely on retrieving personal or confidential records.

Additional guidance:
- If the query suggests accessing personal or confidential data from an HR system, favor "NEED_DB."
- If it’s a general question about company policies or other information that does not require database lookup, choose "NO_DB."

Examples (HR-related context):

1)  
Q: "내 이번 달 퇴근 시간 기록 좀 알려줘."  
A: "NEED_DB"  
(Explanation: Request for personal attendance data stored in an HR system.)

2)  
Q: "사내 조직도 좀 보여줄 수 있어?"  
A: "NEED_DB"  
(Explanation: Organizational charts or team structures are often in a database.)

3)  
Q: "승진 기준이 어떻게 돼?"  
A: "NO_DB"  
(Explanation: Promotion criteria are typically outlined in policy documents or FAQs, not individual records.)

4)  
Q: "내 지난주 연차 사용 내역 알려줘."  
A: "NEED_DB"  
(Explanation: Specific leave records are stored in an HR database.)

5)  
Q: "사내 식당 메뉴가 궁금해."  
A: "NO_DB"  
(Explanation: Can be answered via general information or a public schedule.)

6)  
Q: "나 이번 달 급여명세서 좀 볼 수 있을까?"  
A: "NEED_DB"  
(Explanation: Payroll records are maintained in a secure database.)

7)  
Q: "사내 복지 제도는 뭐가 있지?"  
A: "NO_DB"  
(Explanation: General HR policy info, likely in an internal guide or FAQ, not a personal record query.)

Return only one of the following strings based on your classification:
"NEED_DB" or "NO_DB"
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
