from agent.models import (
    hrdatabase_employee,
    hrdatabase_teammanagement,
    hrdatabase_hrmastercode,
)


def get_user_role(slack_id: str) -> dict:
    """
    주어진 Slack ID를 바탕으로 다음 정보를 반환한다.
    - employee_id: 직원 ID
    - name: 직원 이름
    - rank_name: 직급명
    - department_name: 부서명
    - team_name: 팀명
    - team_leader: boolean 값, 팀장 여부

    찾지 못한 경우 빈 dict 반환
    """
    try:
        # 1. Slack ID로 직원 정보 조회
        employee = hrdatabase_employee.objects.get(slack_id=slack_id)
    except hrdatabase_employee.DoesNotExist:
        return {}

    # 2. rank_code -> 직급명 매핑
    rank_code = employee.employee_level
    rank_name = None
    if rank_code:
        try:
            rank_entry = hrdatabase_hrmastercode.objects.get(code=rank_code)
            rank_name = rank_entry.code_name
        except hrdatabase_hrmastercode.DoesNotExist:
            rank_name = "알 수 없음(미등록 코드)"

    # 3. TeamManagement에서 employee_id로 팀 정보 조회
    try:
        tm = hrdatabase_teammanagement.objects.get(employee_id=employee)
    except hrdatabase_teammanagement.DoesNotExist:
        tm = None

    team_name = None
    department_name = None
    team_leader = False

    if tm:
        team_leader = tm.team_leader
        # team_id -> 팀명
        if tm.team_id:
            try:
                team_code = hrdatabase_hrmastercode.objects.get(code=tm.team_id)
                team_name = team_code.code_name
            except hrdatabase_hrmastercode.DoesNotExist:
                team_name = "알 수 없음(미등록 팀 코드)"

        # department -> 부서명
        if tm.department:
            try:
                dept_code = hrdatabase_hrmastercode.objects.get(code=tm.department)
                department_name = dept_code.code_name
            except hrdatabase_hrmastercode.DoesNotExist:
                department_name = "알 수 없음(미등록 부서 코드)"

    return {
        "employee_id": employee.employee_id,
        "name": employee.employee_name,  # hrdatabase_employee.employee_name
        "rank_name": rank_name,
        "department_name": department_name,
        "team_name": team_name,
        "team_leader": team_leader,
    }


def get_access_level(user_info: dict) -> str:
    managerial_ranks = ["부장"]
    rank_name = user_info.get("rank_name", "")
    department_name = user_info.get("department_name", "")
    team_name = user_info.get("team_name", "")
    team_leader = user_info.get("team_leader", False)

    # 인사팀 여부 판단 (예: 지원부-인사팀)
    if "지원부" in department_name and "인사팀" in team_name:
        return "ALL_ACCESS"

    # 관리직급 판단
    if rank_name in managerial_ranks:
        return "DEPARTMENT_ACCESS"

    # 팀장 판단
    if team_leader:
        return "TEAM_ACCESS"

    # 일반 직원
    return "SELF_ONLY"
