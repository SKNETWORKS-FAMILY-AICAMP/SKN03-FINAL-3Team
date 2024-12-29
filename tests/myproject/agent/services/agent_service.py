import logging
from agent.services.role_service import get_user_role
from agent.services.intent_service import classify_intent
from agent.services.cot_service import apply_cot
from agent.services.query_service import extract_sql_query, execute_sllm_generated_query
from agent.services.format_service import get_formatted_response

logger = logging.getLogger("agent")


def process_user_message(user_message: str, slack_id: str) -> str:
    # 1. 사용자 정보 조회
    user_info = get_user_role(
        slack_id
    )  # {name, rank_name, department_name, team_name, team_leader}
    if not user_info:
        logger.info(f"사용자 정보 없음 (slack_id={slack_id})")
        return "해당 Slack 사용자를 찾을 수 없습니다. 회사 시스템에 등록되지 않은 사용자입니다."

    # 2. 의도 분류
    intent = classify_intent(user_message)
    logger.debug(
        f"사용자 의도: {intent}, 사용자: {user_info['name']}({slack_id}), 팀: {user_info['team_name']}, 직급: {user_info['rank_name']}"
    )

    # 3. 직급별 권한 정의 (예: 부장 이상이면 일부 정보 접근 가능)
    # 직급명(RANKxx)이 '부장'이면 RANK06임을 가정.
    # 실제로는 code_name으로 비교하지 않고 code로 비교(RANK06)하거나, CommonCode 매핑을 캐싱해서 비교할 수 있음.
    # 여기서는 직급명이 '부장'인지만 간단히 체크
    is_executive = user_info["rank_name"] in [
        "부장"
    ]  # 예: 과장 이상이면 관리직급으로 가정
    is_high_level = user_info["team_name"] in ["인사팀"]

    # 4. 쿼리 필요 여부 판단
    # 단순 예: hr_query, complex인 경우 쿼리가 필요하다고 가정.
    needs_query = intent in ["hr_query", "complex"]

    # 5. 접근 가능 여부 판단 (권한 로직)
    # 사용자가 자신의 정보나 동일 팀/부서 정보만 접근 가능하도록 제한할 수 있음.
    # 여기서는 예시로, 팀장 또는 높은 직급일 경우 팀/부서 범위 정보 접근 허용.
    # 일반 사원은 자신의 정보만 접근 가능.
    can_access = True
    if needs_query:
        # 만약 user_message에 특정한 타 부서나 타 팀 언급이 있다면(간단한 가정), is_high_level 또는 team_leader가 아니라면 거부
        # 이 부분은 자연어 처리 필요하거나 simple rule 기반으로 구현할 수 있음.
        # 여기서는 예를 들어 "다른 팀" 또는 "다른 부서"라는 키워드가 있으면 권한 필요하다고 가정.
        if "다른 팀" in user_message or "타팀" in user_message:
            if not user_info["team_leader"] and not is_executive:
                can_access = False

        # 본인보다 높은 레벨 정보(예: 경영진 정보)를 요청하는 경우
        if "경영진 정보" in user_message and not is_high_level:
            can_access = False

    if not can_access:
        logger.warning(f"권한 부족: {user_info['name']}({slack_id}) 요청 거부")
        return "죄송하지만 해당 정보를 조회할 권한이 없습니다."

    # 6. 필요하다면 CoT + LLM을 통해 SQL 생성
    # LLM 프롬프트 개선: 사용자 정보(직급, 팀장 여부, 팀명, 부서명)도 전달
    if needs_query:
        enhanced_prompt = f"""
        사용자 직급: {user_info['rank_name']}
        팀장 여부: {"예" if user_info['team_leader'] else "아니오"}
        부서: {user_info['department_name']}
        팀: {user_info['team_name']}
        해당 사용자의 권한 범위 내에서 SQL을 생성하세요.
        질문: {user_message}
        """

        sllm_response = apply_cot(enhanced_prompt, user_info["rank_name"])

        sql_query = extract_sql_query(sllm_response)
        if not sql_query:
            logger.error(
                f"SQL 추출 실패: LLM 응답에서 SQL을 찾을 수 없음. 사용자: {user_info['name']}({slack_id})"
            )
            return "죄송합니다, 적절한 응답을 생성할 수 없습니다."

        query_result = execute_sllm_generated_query(sql_query, slack_id)
        if isinstance(query_result, str):
            # query_result가 에러 메시지
            logger.error(
                f"쿼리 실행 에러: {query_result}, 사용자: {user_info['name']}({slack_id})"
            )
            return query_result

        # 7. 결과 포맷팅
        formatted_response = get_formatted_response(
            user_info["rank_name"], user_message, query_result
        )
        return formatted_response
    else:
        # 쿼리 없이 처리 가능한 일반 응답(FAQ 등)
        # 필요 시 이 부분에 LLM 호출 없이 답변 반환
        logger.debug(f"쿼리 불필요 응답 처리: {user_info['name']}({slack_id})")
        return "해당 정보는 별도 조회 없이도 안내 가능한 내용입니다."
