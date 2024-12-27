# modules/preprocessor.py

import re
from konlpy.tag import Okt
from .config import PERSONAL_INFO_PATTERNS, MODERATION_KEYWORDS

okt = Okt()

def sanitize_user_input(user_query):
    for pattern in PERSONAL_INFO_PATTERNS:
        user_query = re.sub(pattern, "[REDACTED]", user_query)
    return user_query

def sanitize_documents(documents):
    sanitized_docs = []
    for doc in documents:
        sanitized_i = doc["instruction"]
        sanitized_r = doc["response"]
        for pattern in PERSONAL_INFO_PATTERNS:
            sanitized_i = re.sub(pattern, "[REDACTED]", sanitized_i)
            sanitized_r = re.sub(pattern, "[REDACTED]", sanitized_r)
        sanitized_docs.append({"instruction": sanitized_i, "response": sanitized_r})
    return sanitized_docs

def prevent_prompt_injection(query):
    # "SYSTEM:" 또는 "DEVELOPER:" 같은 문자열 제거
    injection_keywords = ["SYSTEM:", "DEVELOPER:"]
    for kw in injection_keywords:
        query = query.replace(kw, "")
        query = query.replace(kw.lower(), "")
    return query

def extract_keywords(query, top_n=5):
    nouns = okt.nouns(query)
    freq = {}
    for n in nouns:
        freq[n] = freq.get(n, 0) + 1
    sorted_nouns = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, c in sorted_nouns[:top_n]]

def moderate_output(response):
    for kw in MODERATION_KEYWORDS:
        if kw in response:
            return "출력 불가한 내용이 감지되었습니다."
    return response
