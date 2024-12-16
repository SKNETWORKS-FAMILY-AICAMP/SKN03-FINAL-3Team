from agent.models import Employee, TeamManagement, CommonCode


def get_user_role(slack_id: str) -> dict:
    """
    주어진 Slack ID를 바탕으로 다음 정보를 반환한다.
    - name: 직원 이름
    - rank_name: 직급명 (예: '대리', '과장' 등)
    - department_name: 부서명 (예: '개발부')
    - team_name: 팀명 (예: '개발1팀')
    - team_leader: boolean 값, 팀장 여부

    찾지 못한 경우 빈 dict 반환 (또는 적절한 예외처리)
    """
    try:
        # 1. Slack ID로 직원 정보 조회
        employee = Employee.objects.get(slack_id=slack_id)
    except Employee.DoesNotExist:
        # 해당 Slack ID의 직원이 없는 경우
        return {}

    # 2. rank 코드값 -> 직급명 변환
    rank_code = employee.rank
    rank_name = None
    if rank_code:
        try:
            rank_entry = CommonCode.objects.get(code=rank_code)
            rank_name = rank_entry.code_name
        except CommonCode.DoesNotExist:
            rank_name = "알 수 없음(미등록 코드)"

    # 3. TeamManagement에서 employee_id로 팀 정보 조회
    try:
        tm = TeamManagement.objects.get(employee=employee)
    except TeamManagement.DoesNotExist:
        # 팀 정보가 없으면 기본값 처리
        tm = None

    # 4. team_id, department_id 코드명 변환
    team_name = None
    department_name = None
    team_leader = False

    if tm:
        team_leader = tm.team_leader

        # team_id -> 팀명 변환
        if tm.team_id:
            try:
                team_code = CommonCode.objects.get(code=tm.team_id)
                team_name = team_code.code_name
            except CommonCode.DoesNotExist:
                team_name = "알 수 없음(미등록 팀 코드)"

        # department_id -> 부서명 변환
        if tm.department_id:
            try:
                dept_code = CommonCode.objects.get(code=tm.department_id)
                department_name = dept_code.code_name
            except CommonCode.DoesNotExist:
                department_name = "알 수 없음(미등록 부서 코드)"

    # 결과 반환
    return {
        "name": employee.name,
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
