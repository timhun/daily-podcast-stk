import os
import json
import datetime
from fetch_market_data import get_market_data_by_mode
from generate_script_grok import generate_script_from_grok
import requests

# 取得模式與日期
mode = os.getenv("PODCAST_MODE", "us")
now = datetime.datetime.now(datetime.timezone.utc)
today_str = now.strftime("%Y%m%d")
output_dir = f"docs/podcast/{today_str}-{mode}"
os.makedirs(output_dir, exist_ok=True)
script_path = f"{output_dir}/script.txt"

# 擷取行情資料
market_data = get_market_data_by_mode(mode)

# 讀取主題
theme_text = ""
theme_file = "themes.txt"
if os.path.exists(theme_file):
    with open(theme_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
        if lines:
            theme_text = lines[-1].strip()
            if not theme_text.endswith(("。", "！", "？")):
                theme_text += "。"

# 讀取 prompt 模板
prompt_template_path = f"prompt/{mode}.txt"
if not os.path.exists(prompt_template_path):
    raise FileNotFoundError(f"找不到對應的 prompt 模板：{prompt_template_path}")

with open(prompt_template_path, "r", encoding="utf-8") as f:
    prompt_template = f.read()

prompt = prompt_template.replace("{{market_data}}", market_data).replace("{{theme_text}}", f"\n請以以下主題切入角度撰寫：{theme_text}" if theme_text else "")

# 嘗試 Grok 產生
def generate_with_grok():
    try:
        print("🤖 使用 Grok 嘗試產生逐字稿...")
        result = generate_script_from_grok(prompt)
        if result:
            print("✅ 成功使用 Grok 產生逐字稿")
            return result
        raise Exception("Grok 回傳為空")
    except Exception as e:
        print(f"⚠️ Grok 失敗： {e}")
        return None

# 嘗試 Kimi 產生
def generate_with_kimi():
    print("🔁 改用 Kimi API 產生逐字稿...")
    api_key = os.getenv("MOONSHOT_API_KEY")
    if not api_key:
        raise ValueError("請設定 MOONSHOT_API_KEY")

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
        return response.json()["choices"][0]["message"]["content"].strip()
    else:
        print("❌ Kimi API 發生錯誤：", response.status_code, response.text)
        raise RuntimeError("Kimi 回傳錯誤")

# 主流程
script_text = generate_with_grok() or generate_with_kimi()

# 儲存逐字稿
with open(script_path, "w", encoding="utf-8") as f:
    f.write(script_text)

print(f"✅ 已儲存逐字稿至：{script_path}")
