import os
import json
import datetime
import requests

from fetch_market_data import get_market_summary
#from fetch_ai_topic import get_ai_topic_text
from generate_script_grok import generate_script_from_grok
from generate_script_openrouter import generate_script_from_openrouter
from utils_podcast import (
    get_podcast_mode,
    get_today_display,
    is_weekend_prompt,
    TW_TZ,
)

# === 基本設定 ===
PODCAST_MODE = get_podcast_mode()
now = datetime.datetime.now(TW_TZ)
today_str = now.strftime("%Y%m%d")
today_display = get_today_display()

# 輸出路徑
output_dir = f"docs/podcast/{today_str}_{PODCAST_MODE}"
os.makedirs(output_dir, exist_ok=True)
script_path = os.path.join(output_dir, "script.txt")
summary_path = os.path.join(output_dir, "summary.txt")

# 取得行情摘要與 AI 主題
market_data = get_market_summary(PODCAST_MODE)

# 多空判斷（僅台股支援）
bullish_signal = ""
if PODCAST_MODE == "tw":
    signal_path = "docs/podcast/bullish_signal_tw.txt"
    if os.path.exists(signal_path):
        with open(signal_path, "r", encoding="utf-8") as f:
            bullish_signal = f.read().strip()

# 主題檔案（非必須）
theme_text = ""
theme_file = f"prompt/theme-{PODCAST_MODE}.txt"
if os.path.exists(theme_file):
    with open(theme_file, "r", encoding="utf-8") as f:
        raw = f.read().strip()
        if raw:
            theme_text = raw if raw[-1] in "。！？" else raw + "。"

# 判斷是否使用週末 prompt
is_weekend = is_weekend_prompt(PODCAST_MODE, now)
prompt_file = f"prompt/{PODCAST_MODE}{'_weekend' if is_weekend else ''}.txt"
if not os.path.exists(prompt_file):
    raise FileNotFoundError(f"❌ 缺少 prompt 檔案：{prompt_file}")

with open(prompt_file, "r", encoding="utf-8") as f:
    prompt_template = f.read()

# === 組合完整 prompt ===
prompt = prompt_template.format(
    date=today_display,
    market_data=market_data,
    bullish_signal=bullish_signal
)

# === 優先順序：Grok → Kimi → OpenRouter ===

def generate_with_grok():
    try:
        print("🤖 使用 Grok 嘗試產生逐字稿...")
        result = generate_script_from_grok(prompt)
        if result:
            print("✅ 成功使用 Grok 產生逐字稿")
            return result
        raise Exception("Grok 回傳為空")
    except Exception as e:
        print(f"⚠️ Grok 失敗：{e}")
        return None

def generate_with_kimi():
    try:
        print("🔁 改用 Kimi API...")
        api_key = os.getenv("MOONSHOT_API_KEY")
        if not api_key:
            raise ValueError("❌ 未設定 MOONSHOT_API_KEY")

        response = requests.post(
            url="https://api.moonshot.cn/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "moonshot-v1-128k",
                "messages": [
                    {"role": "system", "content": "你是專業的 Podcast 撰稿助手"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2048,
                "top_p": 0.95
            }
        )
        if response.status_code == 200:
            print("✅ 成功使用 Kimi 產生逐字稿")
            return response.json()["choices"][0]["message"]["content"].strip()
        else:
            raise RuntimeError(f"Kimi API 錯誤：{response.status_code}, {response.text}")
    except Exception as e:
        print(f"⚠️ Kimi 失敗：{e}")
        return None

def generate_with_openrouter():
    try:
        print("📡 嘗試使用 OpenRouter GPT-4...")
        result = generate_script_from_openrouter(prompt)
        if result:
            print("✅ 成功使用 OpenRouter GPT-4")
            return result
        raise Exception("OpenRouter 回傳為空")
    except Exception as e:
        print(f"⚠️ OpenRouter 失敗：{e}")
        return None

# === 實際產生逐字稿 ===
script_text = generate_with_grok() or generate_with_kimi() or generate_with_openrouter()
if not script_text:
    raise RuntimeError("❌ 所有來源皆失敗")

# 儲存逐字稿
with open(script_path, "w", encoding="utf-8") as f:
    f.write(script_text)
print(f"✅ 已儲存逐字稿至：{script_path}")

# 摘要產出（前200字）
summary_text = script_text.strip().replace("\n", "").replace("  ", "")[:200]
with open(summary_path, "w", encoding="utf-8") as f:
    f.write(summary_text)
print(f"✅ 已產出節目摘要至：{summary_path}")
