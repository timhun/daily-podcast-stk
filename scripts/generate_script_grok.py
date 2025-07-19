import os
import datetime
import requests

GROK_API_URL = "https://api.x.ai/v1/chat/completions"  # 假設為範例 API，請更換為實際端點
GROK_API_KEY = os.getenv("GROK_API_KEY")  # 環境變數中取得 API 金鑰

def generate_script_from_grok(prompt: str) -> str:
    """
    呼叫 Grok API 產生 Podcast 逐字稿，並儲存至 docs/podcast/{YYYYMMDD}/script.txt
    """
    if not GROK_API_KEY:
        raise RuntimeError("❌ GROK3_API_KEY 環境變數未設定")

    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "grok-3",
        "messages": [
            {"role": "system", "content": "你是專業的 Podcast 撰稿助手"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2048
    }

    print("🤖 使用 Grok3 嘗試產生逐字稿...")

    response = requests.post(GROK_API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        result = response.json()
        script = result["choices"][0]["message"]["content"].strip()

        # 儲存至對應路徑
        today = datetime.datetime.utcnow().strftime("%Y%m%d")
        output_dir = f"docs/podcast/{today}"
        os.makedirs(output_dir, exist_ok=True)
        output_path = f"{output_dir}/script.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(script)

        print(f"✅ Grok 成功產出並儲存逐字稿：{output_path}")
        return script

    else:
        print("❌ Grok3 API 回傳失敗：", response.status_code, response.text)
        raise RuntimeError("Grok3 回傳錯誤")
