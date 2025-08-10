# grok_api.py
import os
from openai import OpenAI
from time import sleep
from requests.exceptions import RequestException

def optimize_script_with_grok(initial_script, api_key, model="grok-4", max_retries=3):
    """
    使用 xAI Grok API 優化 Podcast 逐字稿。
    :param initial_script: 初始逐字稿
    :param api_key: xAI API 密鑰
    :param model: Grok 模型名稱（預設 grok-4）
    :param max_retries: 最大重試次數
    :return: 優化後的逐字稿或初始逐字稿（若 API 失敗）
    """
    if not api_key:
        print("未找到 XAI_API_KEY，使用初始逐字稿")
        return initial_script

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1"
    )

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
                sleep(2 ** attempt)  # 指數退避
            continue
    print(f"Grok API 調用失敗 {max_retries} 次，使用初始逐字稿")
    return initial_script