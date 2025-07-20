import os
import requests

GROK_API_URL = os.getenv("GROK_API_URL")
GROK_API_KEY = os.getenv("GROK_API_KEY")

def generate_script_from_grok(user_prompt: str) -> str:
    if not GROK_API_URL or not GROK_API_KEY:
        raise ValueError("請設定環境變數 GROK_API_URL 與 GROK_API_KEY")

    mode = os.getenv("PODCAST_MODE", "us")
    preface = (
        "請用台灣財經 podcast 主持人風格撰寫，加入對 AI、ETF 與台股的觀察與評論：\n"
        if mode == "tw"
        else "請用專業科技與投資口吻，融合美股、ETF 與最新 AI 趨勢分析：\n"
    )

    prompt = preface + user_prompt

    try:
        print("📡 正在呼叫 Grok API...")
        response = requests.post(
            url=GROK_API_URL,
            headers={"Authorization": f"Bearer {GROK_API_KEY}"},
            json={"messages": [{"role": "user", "content": prompt}]}
        )
        response.raise_for_status()
        data = response.json()

        print("🔍 [Grok] 回傳 JSON：", data)

        reply = data["choices"][0]["message"]["content"].strip()
        if not reply:
            raise RuntimeError("❌ Grok API 回傳內容為空")
        return reply

    except Exception as e:
        raise RuntimeError(f"❌ Grok API 回傳錯誤：{e}")