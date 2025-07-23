# scripts/fetch_ai_topic.py
import os
import json
import pytz
import datetime
from pathlib import Path
import openai  # 或改用你已有的 Kimi / Grok 統一封裝

# ✅ 使用台灣時區
tz = pytz.timezone("Asia/Taipei")
now = datetime.datetime.now(tz)
date_str = now.strftime("%Y%m%d")
today_display = now.strftime("%Y年%m月%d日")
mode = os.getenv("PODCAST_MODE", "us")
folder = Path(f"docs/podcast/{date_str}_{mode}")
folder.mkdir(parents=True, exist_ok=True)

# ✅ 呼叫 GPT-4 產生兩則 AI 主題
openai.api_key = os.getenv("OPENAI_API_KEY")

prompt = f"""
請以中文提供兩則今日最新的 AI 工具或新創公司相關新聞摘要，包含名稱、用途與亮點。內容需適合用在 Podcast 中口語播報，避免太技術性，長度約 200~400 字，格式如下：

1️⃣ xxx
2️⃣ xxx

今日是 {today_display}，請根據最新資料撰寫。
"""

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}],
    temperature=1.0,
)

ai_topic = response.choices[0].message.content.strip()
(Path(folder) / "ai_topic.txt").write_text(ai_topic, encoding="utf-8")
print("✅ 已產出 ai_topic.txt")