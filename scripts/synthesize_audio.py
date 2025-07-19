import os
import datetime
from edge_tts import Communicate
import asyncio

# 日期與模式
mode = os.getenv("PODCAST_MODE", "us")
today = datetime.datetime.utcnow().strftime("%Y%m%d")
base_dir = f"docs/podcast/{today}-{mode}"
script_path = os.path.join(base_dir, "script.txt")
audio_path = os.path.join(base_dir, "audio.mp3")

if not os.path.exists(script_path):
    raise FileNotFoundError(f"⚠️ 找不到逐字稿：{script_path}")

with open(script_path, "r", encoding="utf-8") as f:
    text = f.read()

VOICE = "zh-TW-YunJheNeural"
RATE = "+15%"

async def synthesize():
    communicate = Communicate(text, voice=VOICE, rate=RATE)
    await communicate.save(audio_path)
    print(f"✅ 語音合成完成：{audio_path}")

asyncio.run(synthesize())
