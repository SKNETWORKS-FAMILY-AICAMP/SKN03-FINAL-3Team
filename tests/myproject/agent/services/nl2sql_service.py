def get_sql_from_model(user_message, user_info, access_level):
    # NL2SQL 모델 호출 로직 필요
    # 여기서는 단순 예시
    # access_level에 따라 필터링 조건 추가
    if access_level == "DEPARTMENT_ACCESS":
        return "SELECT * FROM employees WHERE department='개발부';"
    else:
        return "SELECT name, annual_leave FROM employees WHERE name='홍길동';"
