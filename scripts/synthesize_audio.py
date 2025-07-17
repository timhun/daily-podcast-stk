import os
import asyncio
from edge_tts import Communicate

# 確保資料夾存在
os.makedirs("podcast/latest", exist_ok=True)

input_path = "podcast/latest/script.txt"
output_path = "podcast/latest/audio.mp3"

# 確認逐字稿存在
if not os.path.exists(input_path):
    raise FileNotFoundError("⚠️ 找不到 script.txt，無法合成語音")

# 讀取逐字稿內容
with open(input_path, "r", encoding="utf-8") as f:
    text = f.read().strip()

# 語音設定
VOICE = "zh-TW-YunJheNeural"   # 台灣男聲
RATE = "+30%"                  # 語速加快 30%

async def main():
    communicate = Communicate(text=text, voice=VOICE, rate=RATE)
    await communicate.save(output_path)

asyncio.run(main())

print("✅ 已使用 edge-tts Python API 完成語音合成")
