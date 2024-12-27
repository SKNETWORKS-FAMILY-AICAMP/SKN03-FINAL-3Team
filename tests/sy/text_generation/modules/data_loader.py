# modules/data_loader.py

import json
import re
from .config import QA_DATASET_PATH

def load_qa_dataset():
    qa_dataset = []
    with open(QA_DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line.strip())
            instruction = item.get("instruction")
            response = item.get("response") or item.get("answer")
            if instruction and response:
                # 1. instruction에서 넘버링 제거
                instruction = re.sub(r'^\d+\.\s*', '', instruction)
                # 2. response에서 **텍스트** 마크다운 제거
                response = re.sub(r'\*\*(.*?)\*\*', r'\1', response)
                # 3. response에서 \n+\d+. 패턴 제거
                response = re.sub(r'\n+\d+\.', '', response)
                qa_dataset.append({
                    "instruction": instruction,
                    "response": response
                })
    return qa_dataset
