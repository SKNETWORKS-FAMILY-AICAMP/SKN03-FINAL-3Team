# modules/inference.py

import torch
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel, PeftConfig
from .config import SYSTEM_INSTRUCTIONS, FINE_TUNED_MODEL_PATH, FALLBACK_ANSWER
from .preprocessor import moderate_output

def build_few_shot_prompt(user_instruction, similar_qas):
    examples_str = ""
    for qa in similar_qas:
        examples_str += f"Instruction: {qa['instruction']}\nResponse: {qa['response']}\n\n"

    prompt = f"""{SYSTEM_INSTRUCTIONS}

아래는 인스트럭션과 응답 예시입니다:
{examples_str}
이제 아래 인스트럭션에 대해 위와 비슷한 형식으로 정확하고 관련 있는 답변을 해주세요:
Instruction: {user_instruction}
Response:"""
    return prompt

class QAModel:
    def __init__(self):
        # 1. PEFT Config 로드
        peft_config = PeftConfig.from_pretrained(FINE_TUNED_MODEL_PATH)
        base_model_name = peft_config.base_model_name_or_path  # "CohereForAI/aya-expanse-8b"

        # 2. 기본 모델 로드 (device_map 설정)
        self.base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            device_map="auto" if torch.cuda.is_available() else "cpu"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(base_model_name)

        # 3. PEFT 어댑터 로드
        self.model = PeftModel.from_pretrained(
            self.base_model,
            FINE_TUNED_MODEL_PATH,
            device_map="auto" if torch.cuda.is_available() else "cpu"
        )

        # 4. Inference Pipeline 설정 (device 인자 제거)
        self.generator = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer
            # device=0 if torch.cuda.is_available() else -1  # 제거
        )

    def generate_answer(self, prompt):
        try:
            outputs = self.generator(
                temperature=0.2,
                do_sample=True,
                truncation=True,
                repetition_penalty=1.0,
                use_cache=True,
            )
            raw_answer = outputs[0]["generated_text"]
        except Exception:
            raw_answer = FALLBACK_ANSWER
        final_answer = moderate_output(raw_answer)
        return final_answer
