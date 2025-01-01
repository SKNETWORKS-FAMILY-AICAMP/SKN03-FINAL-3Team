import requests


def query_sllm(prompt: str, num_return_sequences=1):
    payload = {"prompt": prompt, "num_return_sequences": num_return_sequences}
    response = requests.post("http://localhost:8000/sllm/generate/", json=payload)
    data = response.json()
    if num_return_sequences > 1:
        return data["text"]
    return data["text"]
