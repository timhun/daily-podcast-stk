# scripts/generate_script_openai.py

import os
import openai

def generate_script_from_openai(user_prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("請設定 OPENAI_API_KEY 環境變數")

    model = os.getenv("OPENAI_MODEL", "gpt-4")

    try:
        client = openai.OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是專業的 Podcast 撰稿助手"},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            top_p=0.95
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ OpenAI API 發生錯誤：", e)
        return None