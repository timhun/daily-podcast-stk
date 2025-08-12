# grok_api.py
import os
from openai import OpenAI
from time import sleep
from requests.exceptions import RequestException
import requests
import json
import re

GROK_API_URL = os.getenv("GROK_API_URL", "https://api.x.ai/v1/chat/completions")
GROK_API_KEY = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")

def optimize_script_with_grok(initial_script, api_key, model="grok-4", max_retries=3):
    if not api_key:
        print("未找到 XAI_API_KEY，使用初始逐字稿")
        return initial_script

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )
    except Exception as e:
        print(f"Failed to initialize OpenAI client: {e}")
        return initial_script

    prompt = (
        "你是一位專業財經科技主持人，名叫幫幫忙，請根據以下初始逐字稿，使用繁體中文撰寫一段約10分鐘的Podcast播報逐字稿，"
        "風格需更口語化、自然，適合廣播節目，控制在3000字以內。請保留所有市場數據（包括收盤價和成交金額，單位為台幣億元），"
        "並融入專業分析，確保內容符合台灣慣用語，保留英文術語（如 Nvidia、Fed）。\n\n"
        f"初始逐字稿：\n{initial_script}\n\n"
        "注意：僅輸出繁體中文逐字稿正文，勿包含任何說明或JSON格式。"
    )

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一位專業財經科技主持人，擅長以口語化方式呈現財經分析。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=3000
            )
            return response.choices[0].message.content
        except RequestException as e:
            print(f"Grok API 調用失敗（嘗試 {attempt + 1}/{max_retries}）：{e}")
            if attempt < max_retries - 1:
                sleep(2 ** attempt)
            continue
    print(f"Grok API 調用失敗 {max_retries} 次，使用初始逐字稿")
    return initial_script

def ask_grok(prompt: str, role: str = "user", model: str = "grok-4") -> str:
    """Call xAI Grok API and return plain text reply."""
    if not GROK_API_KEY:
        raise EnvironmentError("❌ 請設定 GROK_API_KEY 或 XAI_API_KEY 環境變數")

    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": role, "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2048,
        "stream": False,
    }

    resp = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    choices = data.get("choices", [])
    if not choices or not choices[0].get("message", {}).get("content"):
        raise RuntimeError(f"❌ Grok 回傳內容為空或無效：{json.dumps(data, ensure_ascii=False)[:500]}")
    return choices[0]["message"]["content"].strip()


def ask_grok_json(prompt: str, role: str = "user", model: str = "grok-4") -> dict:
    """Call xAI Grok API and parse a JSON object from the reply."""
    reply = ask_grok(prompt, role=role, model=model)
    json_match = re.search(r"\{[\s\S]*\}", reply, re.DOTALL)
    if not json_match:
        raise ValueError(f"❌ Grok 回傳不是合法 JSON：\n{reply[:1000]}")
    json_str = json_match.group(0)
    json_str = re.sub(r"(\d+)\.(?!\d)", r"\1.0", json_str)
    json_str = re.sub(r",\s*}", r"}", json_str)
    json_str = re.sub(r",\s*,", r",", json_str)
    return json.loads(json_str)