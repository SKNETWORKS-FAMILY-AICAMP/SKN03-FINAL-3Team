import logging
from typing import Literal

from agent.services.ollama_service import query_ollama_classifier

logger = logging.getLogger("agent")


def classify_db_need(user_message: str) -> Literal["NEED_DB", "NO_DB"]:
    """
    Ollama를 이용해, user_message가 DB 조회가 필요한지(NEED_DB),
    아니면 일반 대화로 처리 가능한지(NO_DB) 분류합니다.
    """

    # 1) 시스템(System) 프롬프트
    system_prompt = """SYSTEM:
You are a specialized classifier that decides if a user query requires a database lookup ("NEED_DB")
or can be addressed without querying any database ("NO_DB").
Follow the criteria and examples strictly. Output exactly "NEED_DB" or "NO_DB" with no extra text.
"""

    # 2) 어시스턴트(Assistant) 지침
    assistant_prompt = """ASSISTANT:
Criteria:

1) NEED_DB
   - The user requests personal or specific data typically stored in internal systems (e.g., HR, payroll, attendance logs, leftover vacation days, tardiness/absences history).
   - Examples of NEED_DB:
     - "내가 이번 달에 지각 몇 번 했어?"
     - "그동안 결근 얼마나 했지?"
     - "내 남은 연차가 며칠이야?"
     - "인사팀 인원 정보 보여줘" (사원 목록/상세)

2) NO_DB
   - The question can be answered without retrieving personal/confidential data from a database.
   - Typically about:
     - General HR policy, company rules, or processes (e.g. “연차 사용 절차,” “학자금 지원 신청 기한” 등)
     - Casual chat, general FAQs, or non-sensitive information that does not involve any individual's records.

Q: "사내 식당 메뉴가 궁금해."
A: "NO_DB"

Q: "인사팀 인원 정보 보여줘."
A: "NEED_DB"

Q: "내가 이번 달에 지각 몇 번 했어?"
A: "NEED_DB"

Q: "그동안 결근 얼마나 했지?"
A: "NEED_DB"

Q: "연차를 사용할 때 필요한 조건이 뭐야?"
A: "NO_DB"
(Explanation: This asks for a general company rule/policy.)

Q: "학자금 지원 신청의 기한이 언제인지 알고 싶습니다."
A: "NO_DB"
(Explanation: This is about company policy or a general process, not personal data.)

Q: "학자금 지원을 받으려면 어떤 서류가 필요한가요?"
A: "NO_DB"

Q: "아내가 출산하는데 몇 일 쉴 수 있어?"
A: "NO_DB"

Q: "배우자 출산으로 인해 특별휴가를 얼마나 받을 수 있어?"
A: "NO_DB"

Q: "창립기념일이 언제야?"
A: "NO_DB"

Q: "신입사원인데 연차언제부터 사용할 수 있나요?"
A: "NO_DB"


Finally, if the request is not explicitly about personal or sensitive internal data,
default to "NO_DB".
"""

    # 3) 사용자(User) 메시지
    user_prompt = f"Q:\n{user_message}\n"

    # 최종 프롬프트: system → assistant → user 순서로 합침
    final_prompt = f"{system_prompt}\n\n{assistant_prompt}\n\n{user_prompt} A:"

    try:
        # Ollama로 분류 요청
        response_text = query_ollama_classifier(
            prompt=final_prompt, temperature=0.2, max_tokens=50
        )
        logger.debug(f"[classify_db_need] raw_response = {response_text}")

        lines = response_text.strip().splitlines()
        final_line = lines[-1].strip().upper()

        if final_line == "NEED_DB":
            return "NEED_DB"
        elif final_line == "NO_DB":
            return "NO_DB"
        else:
            # fallback: 만약 예상값이 아니면 NO_DB로 처리
            return "NO_DB"

    except Exception as e:
        logger.error(f"메시지 분류 실패: {e}", exc_info=True)
        return "NO_DB"
