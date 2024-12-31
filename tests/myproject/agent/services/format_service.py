# agent/services/format_service.py

import logging

logger = logging.getLogger("agent")


def get_formatted_response(rank_name: str, user_message: str, query_result):
    """
    DB 조회 결과를 일정한 텍스트 형식으로 가공해서 반환.
    예: 표 형태로 만들거나, JSON -> 문자열 변환
    """
    # 단순 예시
    lines = []
    lines.append(f"'{rank_name}'님이 요청하신 내용: {user_message}")
    lines.append("결과 목록:")
    for row in query_result:
        # 예: dict -> "name=홍길동, department=개발팀 ..."
        row_str = ", ".join([f"{k}={v}" for k, v in row.items()])
        lines.append(f" - {row_str}")

    return "\n".join(lines)
