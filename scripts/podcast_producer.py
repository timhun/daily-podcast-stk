# scripts/podcast_producer.py
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import wave
import contextlib

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("podcast_producer")
logger.setLevel(logging.INFO)
fh = RotatingFileHandler(os.path.join(LOG_DIR, "podcast_producer.log"), maxBytes=1_000_000, backupCount=2, encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(fh)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(sh)

def _write_silent_wav(path: str, seconds=2, framerate=22050):
    nframes = seconds * framerate
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        wf.writeframes(b"\x00\x00" * nframes)

def synthesize(script_path: str) -> str:
    if not os.path.exists(script_path):
        raise FileNotFoundError(script_path)
    out_dir = os.path.dirname(script_path)
    wav_path = os.path.join(out_dir, "audio.wav")
    _write_silent_wav(wav_path)
    # 為了簡化，在 CI 直接輸出 wav；若你需要 mp3，可在本地或加 ffmpeg 步驟轉檔
    logger.info(f"已產生靜音音檔（stub）：{wav_path}")
    return wav_path