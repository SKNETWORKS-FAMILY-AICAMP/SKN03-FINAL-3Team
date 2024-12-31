# 간단 예시: 실제로는 모델 로딩 후 분류 로직 수행 가능
intent_classes = ["general", "hr_query", "permission", "unknown"]


def classify_intent(message: str) -> str:
    # 임의 규칙 기반 분류 예시
    if "인사" in message or "근태" in message or "사원" in message:
        return "hr_query"
    return "general"
