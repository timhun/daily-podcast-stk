import os
import requests

def generate_script_from_openrouter(prompt: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("❌ OPENROUTER_API_KEY 環境變數未設定")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "openai/gpt-4",
        "messages": [
            {"role": "system", "content": "你是專業的 Podcast 撰稿助手"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 0.95
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"].strip()
    else:
        raise RuntimeError(f"OpenRouter API 錯誤：{response.status_code}, {response.text}")