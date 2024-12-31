from django.conf import settings
import logging
from agent.models import Employee, TeamManagement, CommonCode, AttendanceManagement
from agent.services.role_service import get_user_role, get_access_level
from django.db.models import Q

# Django ORM에서 F 사용하려면 import 필요
from django.db.models import F


logger = logging.getLogger(__name__)


def process_user_message(user_message: str, slack_id: str) -> str:
    # 1. 사용자 정보 조회 (DB 접근은 role_service.py에서)
    user_info = get_user_role(slack_id)
    if not user_info:
        logger.info(f"사용자 정보 없음 (slack_id={slack_id})")
        return "해당 Slack 사용자를 찾을 수 없습니다. 회사 시스템에 등록되지 않은 사용자입니다."

    # 2. 의도 분류
    intent = classify_intent(user_message)
    logger.debug(
        f"사용자 의도: {intent}, 사용자: {user_info['name']}({slack_id}), "
        f"팀: {user_info['team_name']}, 직급: {user_info['rank_name']}"
    )

    # 3. 직급별 권한 정의 (예: 부장 이상이면 일부 정보 접근 가능)
    is_executive = user_info["rank_name"] in ["부장"]
    is_high_level = user_info["team_name"] in ["인사팀"]

    # 4. 쿼리 필요 여부 판단 (예시)
    needs_query = intent in ["hr_query", "complex"]

    # 5. 접근 가능 여부 판단 (예시 권한 로직)
    can_access = True
    if needs_query:
        if "다른 팀" in user_message or "타팀" in user_message:
            if not user_info["team_leader"] and not is_executive:
                can_access = False
        if "경영진 정보" in user_message and not is_high_level:
            can_access = False

    if not can_access:
        logger.warning(f"권한 부족: {user_info['name']}({slack_id}) 요청 거부")
        return "죄송하지만 해당 정보를 조회할 권한이 없습니다."

    # 6. 필요하다면 CoT + LLM을 통해 SQL 생성
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
                f"SQL 추출 실패: LLM 응답에서 SQL을 찾을 수 없음. "
                f"사용자: {user_info['name']}({slack_id})"
            )
            return "죄송합니다, 적절한 응답을 생성할 수 없습니다."

        query_result = execute_sllm_generated_query(sql_query, slack_id)
        if isinstance(query_result, str):
            # query_result가 에러 메시지일 수 있음
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
        # 8. 쿼리 없이 처리 가능한 일반 응답(FAQ 등)
        logger.debug(f"쿼리 불필요 응답 처리: {user_info['name']}({slack_id})")
        return "해당 정보는 별도 조회 없이도 안내 가능한 내용입니다."
