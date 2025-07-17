import os
import datetime
import asyncio
from edge_tts import Communicate

# 日期
today_str = datetime.datetime.utcnow().strftime("%Y%m%d")

# 檔案路徑
os.makedirs(f"podcast/{today_str}", exist_ok=True)
input_path = "podcast/latest/script.txt"
output_path = f"podcast/{today_str}/audio.mp3"

# 讀取逐字稿
if not os.path.exists(input_path):
    raise FileNotFoundError("⚠️ 找不到 script.txt，無法合成語音")
with open(input_path, "r", encoding="utf-8") as f:
    text = f.read().strip()

# edge-tts 語音設定
VOICE = "zh-TW-YunJheNeural"
RATE = "+30%"

async def main():
    communicate = Communicate(text=text, voice=VOICE, rate=RATE)
    await communicate.save(output_path)

asyncio.run(main())
print(f"✅ 已完成語音合成：{output_path}")