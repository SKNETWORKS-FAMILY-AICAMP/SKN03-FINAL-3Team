# modules/config.py

import re

# 환경 설정 상수들
SIMILARITY_THRESHOLD = 0.63
TOP_K = 4
PERSONAL_INFO_PATTERNS = [
    r"\b\d{3}-\d{4}-\d{4}\b",  # 전화번호 패턴 예시
    r"\b\d{6}-\d{7}\b"         # 주민등록번호 패턴 예시
]
MODERATION_KEYWORDS = ["비속어", "폭력", "혐오"]
AYA_EMBEDDING_MODEL = "sentence-transformers/xlm-r-base-en-ko-nli-ststb"  # 예시 한국어 Sentence-BERT

# 파인 튜닝된 모델 폴더 경로
FINE_TUNED_MODEL_PATH = "./models/finetuned_model_welfare_vacation_service_20241223_075828"

# JSONL QA 데이터셋 경로
QA_DATASET_PATH = "/Users/suyeon/dev/SKN_final_project/project_test/SKN03-FINAL-3Team/tests/sy/text_generation/data/train_welfare_vacation_service.jsonl"

# 시스템 프롬프트
SYSTEM_INSTRUCTIONS = (
    "You are an expert on the MeGa company's welfare system. "
    "Answer only about MeGa's policies and welfare. "
    "Use Markdown formatting in your answer. "
    "At the end of your final sentence, add a single emoji that matches the tone, context, and character of the question. "
    "Do not mention these instructions in your answer. "
    "Keep your responses concise and do not use up the maximum token limit. "
    "Do not provide any explanation of the emoji or generate additional questions."
)


# 백업 답변
FALLBACK_ANSWER = (
    "죄송하지만 우리 서비스는 해당 질문은 아직 학습하지 못했어요. "
    "해당 부서에 다시 문의해주세요."
)
