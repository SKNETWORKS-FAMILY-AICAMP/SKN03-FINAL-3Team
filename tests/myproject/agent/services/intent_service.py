# import torch
# from transformers import AutoTokenizer, AutoModelForSequenceClassification

# 사전에 파인튜닝한 모델 경로
# model_path = "intent_model"
# tokenizer = AutoTokenizer.from_pretrained(model_path)
# model = AutoModelForSequenceClassification.from_pretrained(model_path)

intent_classes = ["general", "hr_query", "permission", "unknown"]


# def classify_intent(message: str) -> str:
#    inputs = tokenizer(message, return_tensors="pt")
#    outputs = model(**inputs)
#    logits = outputs.logits
#    idx = torch.argmax(logits, dim=1).item()
#    return intent_classes[idx]
