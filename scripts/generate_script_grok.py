import os
import requests
import json


def generate_script_from_grok(prompt: str) -> str:
    """
    使用 Grok API 生成逐字稿內容

    參數:
        prompt (str): 用於生成內容的提示詞

    返回:
        str: 成功生成的逐字稿內容
    """
    grok_api_url = os.getenv("GROK_API_URL", "https://api.grokservice.com/v1/chat/completions")
    grok_api_key = os.getenv("GROK_API_KEY")

    if not grok_api_key:
        raise ValueError("請設定環境變數 GROK_API_KEY")

    headers = {
        "Authorization": f"Bearer {grok_api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "grok-1.5",  # 可根據實際型號調整
        "messages": [
            {"role": "system", "content": "你是專業的 Podcast 撰稿助手"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 0.95
    }

    response = requests.post(grok_api_url, headers=headers, json=payload)

    if response.status_code == 200:
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    else:
        raise RuntimeError(f"Grok API 回傳錯誤：{response.status_code} - {response.text}")