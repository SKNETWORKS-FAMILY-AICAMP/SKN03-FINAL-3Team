def execute_sllm_generated_query(sql_query: str, user_id: str):
    # 실제 DB 접속/쿼리 실행 필요
    # 예시로 하드코딩
    if "annual_leave" in sql_query:
        return [{"name": "홍길동", "annual_leave": 10}]
    return [{"name": "홍길동", "department": "개발부"}]
