import os
import requests

def generate_script_from_openrouter(user_prompt: str) -> str:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    if not OPENROUTER_API_KEY:
        raise ValueError("請設定環境變數 OPENROUTER_API_KEY")

    mode = os.getenv("PODCAST_MODE", "us")

    # 前言根據模式調整語氣
    if mode == "tw":
        preface = "你是一位台灣財經 Podcast 主持人，語氣自然、深入、專業，請撰寫一段適合台股與 AI 投資的逐字稿內容：\n"
    else:
        preface = "你是一位專業的美股與科技趨勢 Podcast 主持人，請撰寫內容深入且具有觀點：\n"

    prompt = preface + user_prompt

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4",
                "messages": [
                    {"role": "system", "content": "你是一位專業 Podcast 財經腳本撰稿助手"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
        )

        if response.status_code == 402:
            raise RuntimeError("OpenRouter API 錯誤：402, " + response.text)

        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    except Exception as e:
        raise RuntimeError(f"OpenRouter API 回傳錯誤：{e}")