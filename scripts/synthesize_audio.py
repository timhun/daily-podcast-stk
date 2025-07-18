import os
import datetime
from edge_tts import Communicate
import asyncio

# 今日日期（UTC）
today = datetime.datetime.utcnow().strftime("%Y%m%d")
base_dir = f"docs/podcast/{today}"
script_path = os.path.join(base_dir, "script.txt")
audio_path = os.path.join(base_dir, "audio.mp3")

# 確保逐字稿存在
if not os.path.exists(script_path):
    raise FileNotFoundError(f"⚠️ 找不到逐字稿：{script_path}")

# 讀取逐字稿內容
with open(script_path, "r", encoding="utf-8") as f:
    text = f.read()

# 合成語音參數
VOICE = "zh-TW-YunJheNeural"
RATE = "+15%"

# 使用 edge-tts 的 Python API 合成語音
async def synthesize():
    communicate = Communicate(text, voice=VOICE, rate=RATE)
    await communicate.save(audio_path)
    print(f"✅ 已完成語音合成：{audio_path}")

asyncio.run(synthesize())
