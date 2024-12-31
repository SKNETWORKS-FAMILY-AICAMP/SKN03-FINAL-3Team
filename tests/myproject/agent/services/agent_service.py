from django.conf import settings
import logging
from agent.models import Employee, TeamManagement, CommonCode, AttendanceManagement
from agent.services.role_service import get_user_role, get_access_level
from django.db.models import Q

# Django ORM에서 F 사용하려면 import 필요
from django.db.models import F


logger = logging.getLogger(__name__)


def process_user_message(user_message: str, slack_id: str) -> str:
    try:
        user_info = get_user_role(slack_id)
        if not user_info:
            return "해당 Slack 사용자를 찾을 수 없습니다."
        access_level = get_access_level(user_info)

        if "연차" in user_message or "휴가" in user_message:
            query_result = query_annual_leave_info(user_info, access_level)
            if not query_result:
                return "조회 가능한 연차 정보가 없습니다."

            result_str = "\n".join(
                [
                    f"{row['employee_name']} : {row['remaining_annual_leave']}일"
                    for row in query_result
                ]
            )
            return f"요청하신 연차 정보:\n{result_str}"
        else:
            return "현재 연차 정보 외 다른 기능은 Mock 단계에서는 지원하지 않습니다."
    except Exception as e:
        logger.exception("Exception in process_user_message")
        return "에러가 발생했습니다. 관리자에게 문의해주세요."


def query_annual_leave_info(user_info: dict, access_level: str):
    """
    Access Level에 따라 AttendanceManagement 테이블에서 remaining_annual_leave 조회.
    user_info 예:
    {
        "name": "홍길동",
        "rank_name": "대리",
        "department_name": "개발부",
        "team_name": "개발1팀",
        "team_leader": False
    }
    """

    # 이름, 팀명, 부서명 추출
    employee_name = user_info.get("name")
    department_name = user_info.get("department_name")
    team_name = user_info.get("team_name")

    # 직원 필터링을 위해 Employee에서 조건부 필터 수행
    # 우선 Employee queryset을 만듦
    employees = Employee.objects.all()

    if access_level == "SELF_ONLY":
        # 본인만 조회
        employees = employees.filter(name=employee_name)
    elif access_level == "TEAM_ACCESS":
        # 같은 팀 직원만 조회
        # team_name으로 TeamManagement를 통해 같은 팀 직원 찾기
        # 우선 현재 직원 객체 획득
        try:
            current_emp = Employee.objects.get(name=employee_name)
        except Employee.DoesNotExist:
            return []

        # current_emp와 같은 team_id를 가진 모든 employee 찾기
        # current_emp가 속한 team_id 조회
        try:
            tm = TeamManagement.objects.get(employee=current_emp)
            team_id = tm.team_id
            # 같은 team_id를 가진 모든 employee id 추출
            team_employees = TeamManagement.objects.filter(team_id=team_id).values_list(
                "employee_id", flat=True
            )
            employees = employees.filter(employee_id__in=team_employees)
        except TeamManagement.DoesNotExist:
            # 팀 정보 없음
            return []
    elif access_level == "DEPARTMENT_ACCESS":
        # 같은 부서의 직원 조회
        # department_name이 None일 수 있으므로 체크
        if department_name:
            # department_name → CommonCode의 code를 거쳐 필터하는 로직 필요 시 보완 가능
            # 여기서는 CommonCode 없이 단순히 department_name으로 바로 필터했다고 가정
            # 실제 부서명 필터는 TeamManagement.department_id -> CommonCode 매핑 필요.
            # 간단히 팀관리 테이블의 department_id를 이용해서 employee 집합을 만들 수도 있다.
            # 여기서는 부서명을 가진 모든 팀조회 → 그 팀에 속한 사원전체 조회 구현 예시

            # department_id 찾기 (CommonCode에서 department_name 매핑)
            dept_codes = CommonCode.objects.filter(
                code_name=department_name
            ).values_list("code", flat=True)
            # 해당 부서 코드를 가진 팀들 찾기
            team_emp_ids = TeamManagement.objects.filter(
                department_id__in=dept_codes
            ).values_list("employee_id", flat=True)
            employees = employees.filter(employee_id__in=team_emp_ids)
        else:
            return []
    elif access_level == "ALL_ACCESS":
        # 모든 직원 가능하니 그대로 employees 사용
        pass
    else:
        # 정의되지 않은 권한
        return []

    # 이제 employees 쿼리셋에 해당하는 직원들의 연차 정보 조회
    # AttendanceManagement와 Employee는 FK 연결
    attendance_qs = AttendanceManagement.objects.filter(employee__in=employees)
    # 원하는 필드(이름, 연차) 추출
    results = (
        attendance_qs.annotate(employee_name=F("employee__name"))
        .values("employee_name", "remaining_annual_leave")
        .order_by("employee_name")
    )

    return list(results)
