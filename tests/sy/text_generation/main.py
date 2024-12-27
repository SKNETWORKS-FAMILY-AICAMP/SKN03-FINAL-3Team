# main.py

import nltk
import sys
import os

# OpenMP 스레드 수 제한
os.environ["OMP_NUM_THREADS"] = "1"

# NLTK 데이터 다운로드 (최초 실행 시에만 필요)
nltk.download('punkt', quiet=True)

from modules.data_loader import load_qa_dataset
from modules.faiss_indexer import FaissIndexer
from modules.preprocessor import (
    sanitize_user_input,
    prevent_prompt_injection,
    extract_keywords,
    sanitize_documents
)
from modules.inference import QAModel, build_few_shot_prompt
from modules.utils import has_access

def main(user_queries, user_token="dummy_token"):
    # 1) QA 데이터 로드
    qa_dataset = load_qa_dataset()

    # 2) Faiss 인덱스 생성
    indexer = FaissIndexer(qa_dataset)
    indexer.build_index()

    # 3) 파인튜닝된 모델 로드
    qa_model = QAModel()

    # 사용자 입력 목록 처리
    results = []
    for user_input in user_queries:
        # 1) 프롬프트 인젝션 방지
        user_input_processed = prevent_prompt_injection(user_input)

        # 2) 개인정보 제거
        user_input_processed = sanitize_user_input(user_input_processed)

        # 3) 키워드 추출 후 임베딩
        keywords = extract_keywords(user_input_processed, top_n=5)
        search_query = " ".join(keywords) if keywords else user_input_processed
        query_emb = indexer.get_embedding(search_query)

        # 4) 접근 권한 체크
        if not has_access(user_token):
            # 권한이 없을 경우 특정 문구 리턴
            results.append("벡터DB 접근 불가")
            continue

        # 5) 검색
        top_indices, all_sims = indexer.search(query_emb)

        # 해당 QA 쌍들
        if len(top_indices) == 0:
            # 관련 문서가 없는 경우
            results.append("죄송하지만 우리 서비스는 해당 질문은 아직 학습하지 못했어요. 해당 부서에 다시 문의해주세요.")
            continue
        else:
            # 문서 sanitize
            filtered_qas = [qa_dataset[i] for i in top_indices]
            filtered_qas = sanitize_documents(filtered_qas)

            # few-shot prompt 생성
            prompt = build_few_shot_prompt(user_input_processed, filtered_qas)

            # 모델 추론
            final_answer = qa_model.generate_answer(prompt)

            # 결과 저장
            results.append(final_answer)

    return results

if __name__ == "__main__":
    # 예시 질문
    user_queries = [
        "자녀 학자금 신청 방법이 어떻게 되나요?",
        "구내식당은 언제 문을 열고 닫나요? 특히 점심과 저녁 시간대가 궁금해요.",
    ]

    answers = main(user_queries)
    # 최종 결과만 출력
    for ans in answers:
        print(ans)

# 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