import os
import datetime
import asyncio
from edge_tts import Communicate

# 使用台灣時區產生 today 字串
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
today = now.strftime("%Y%m%d")

# 取得 podcast 模式（us 或 tw）
PODCAST_MODE = os.getenv("PODCAST_MODE", "us").lower()

# 路徑組合
base_dir = f"docs/podcast/{today}_{PODCAST_MODE}"
script_path = os.path.join(base_dir, "script.txt")
audio_path = os.path.join(base_dir, "audio.mp3")

# 檢查逐字稿是否存在
if not os.path.exists(script_path):
    raise FileNotFoundError(f"⚠️ 找不到逐字稿：{script_path}")

# 讀取逐字稿內容
with open(script_path, "r", encoding="utf-8") as f:
    text = f.read()

# Edge TTS 設定
VOICE = "zh-TW-YunJheNeural"
RATE = "+15%"

# 語音合成函式
async def synthesize():
    communicate = Communicate(text, voice=VOICE, rate=RATE)
    await communicate.save(audio_path)
    print(f"✅ 已完成語音合成：{audio_path}")

# 執行語音合成
asyncio.run(synthesize())