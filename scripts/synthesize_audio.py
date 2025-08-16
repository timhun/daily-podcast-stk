import os
import datetime
import asyncio
from edge_tts import Communicate
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 使用台灣時區產生 today 字串
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
today = now.strftime("%Y%m%d")

# 取得 podcast 模式（預設 tw）
PODCAST_MODE = os.getenv("PODCAST_MODE", "tw").lower()

# 路徑組合
base_dir = f"docs/podcast/{today}_{PODCAST_MODE}"
script_path = os.path.join(base_dir, "script.txt")
audio_path = os.path.join(base_dir, "audio.mp3")

# 檢查逐字稿是否存在
if not os.path.exists(script_path):
    logger.error(f"⚠️ 找不到逐字稿：{script_path}")
    raise FileNotFoundError(f"⚠️ 找不到逐字稿：{script_path}")

# 讀取逐字稿內容
try:
    with open(script_path, "r", encoding="utf-8") as f:
        text = f.read()
except Exception as e:
    logger.error(f"⚠️ 讀取逐字稿失敗: {e}")
    raise IOError(f"⚠️ 讀取逐字稿失敗: {e}")

# Edge TTS 設定
VOICE = "zh-TW-YunJheNeural"
RATE = "+15%"

# 語音合成函式
async def synthesize():
    try:
        communicate = Communicate(text, voice=VOICE, rate=RATE)
        await communicate.save(audio_path)
        logger.info(f"✅ 已完成語音合成：{audio_path}")
    except Exception as e:
        logger.error(f"⚠️ 語音合成失敗: {e}")
        raise RuntimeError(f"⚠️ 語音合成失敗: {e}")

# 執行語音合成
if __name__ == "__main__":
    asyncio.run(synthesize())
