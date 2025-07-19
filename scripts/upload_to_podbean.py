import os
import json
import datetime
import requests

# 設定日期
today_str = datetime.datetime.utcnow().strftime("%Y%m%d")
identifier = f"daily-podcast-stk-{today_str}"
base_dir = f"docs/podcast/{today_str}"
audio_path = os.path.join(base_dir, "audio.mp3")
script_path = os.path.join(base_dir, "script.txt")

# 驗證檔案存在
if not os.path.exists(audio_path):
    raise FileNotFoundError("❌ 找不到 audio.mp3")
if not os.path.exists(script_path):
    raise FileNotFoundError("❌ 找不到 script.txt")

# 取得環境變數
client_id = os.getenv("PODBEAN_CLIENT_ID")
client_secret = os.getenv("PODBEAN_CLIENT_SECRET")
refresh_token = os.getenv("PODBEAN_REFRESH_TOKEN")

if not all([client_id, client_secret, refresh_token]):
    raise ValueError("請設定 PODBEAN_CLIENT_ID, PODBEAN_CLIENT_SECRET, PODBEAN_REFRESH_TOKEN")

# Step 1: 取得 access_token
token_resp = requests.post("https://api.podbean.com/v1/oauth/token", data={
    "grant_type": "refresh_token",
    "refresh_token": refresh_token,
    "client_id": client_id,
    "client_secret": client_secret
})

if token_resp.status_code != 200:
    raise RuntimeError(f"❌ 無法取得 access_token: {token_resp.text}")

access_token = token_resp.json().get("access_token")
headers = {"Authorization": f"Bearer {access_token}"}

# Step 2: 上傳檔案
print("🔼 正在上傳 MP3 至 Podbean...")
with open(audio_path, "rb") as f:
    upload_resp = requests.post(
        "https://api.podbean.com/v1/files/upload",
        headers=headers,
        files={"file": f}
    )

if upload_resp.status_code != 200:
    raise RuntimeError(f"❌ 音訊檔上傳失敗: {upload_resp.text}")

media_url = upload_resp.json()["file_url"]

# Step 3: 讀取逐字稿
with open(script_path, "r", encoding="utf-8") as f:
    transcript = f.read().strip()

# Step 4: 發佈節目
title = f"幫幫忙每日投資快報 - {today_str}"
publish_data = {
    "title": title,
    "content": transcript,
    "media_url": media_url,
    "status": "public"
}

print("📢 正在發佈節目至 Podbean...")
pub_resp = requests.post("https://api.podbean.com/v1/episodes", headers=headers, data=publish_data)

if pub_resp.status_code == 200:
    print("✅ 成功同步節目至 Podbean！")
else:
    raise RuntimeError(f"❌ 發佈失敗: {pub_resp.text}")
