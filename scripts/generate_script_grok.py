import os
import requests

GROK_API_URL = os.getenv("GROK_API_URL")
GROK_API_KEY = os.getenv("GROK_API_KEY")

def generate_script_from_grok(user_prompt: str) -> str:
    if not GROK_API_URL or not GROK_API_KEY:
        raise ValueError("請設定環境變數 GROK_API_URL 與 GROK_API_KEY")

    mode = os.getenv("PODCAST_MODE", "us")

    # 根據 mode 補強 Grok 提示語氣與口吻
    if mode == "tw":
        preface = "請以台灣財經 podcast 主持人口吻，加入對 AI、半導體、ETF 觀察的自然評論：\n"
    else:
        preface = "請以財經科技主持人語氣，結合美股、ETF、科技新聞做深入分析：\n"

    prompt = preface + user_prompt

    try:
        response = requests.post(
            GROK_API_URL,
            headers={"Authorization": f"Bearer {GROK_API_KEY}"},
            json={"messages": [{"role": "user", "content": prompt}]}
        )
        response.raise_for_status()
        return response.json()["reply"].strip()
    except Exception as e:
        print("❌ Grok API 回傳錯誤：", e)
        return None
