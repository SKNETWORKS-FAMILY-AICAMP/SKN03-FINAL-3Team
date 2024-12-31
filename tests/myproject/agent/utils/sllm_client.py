def query_sllm(prompt: str) -> str:
    # 실제 LLM API 호출 필요
    # 예시로 하드코딩 응답
    # 실제로는 OpenAI API나 로컬 LLM 호출
    if "Action:" in prompt:
        return "Reason: ...\nAction: NO_MORE_ACTIONS\nAction Input:"
    if "DB 조회 결과:" in prompt:
        return "Reason: DB결과 확인 완료\nAction: NO_MORE_ACTIONS\nAction Input:"
    return "이것은 예시 응답입니다."
