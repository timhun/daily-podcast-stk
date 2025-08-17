# scripts/upload_manager.py
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("upload_manager")
logger.setLevel(logging.INFO)
fh = RotatingFileHandler(os.path.join(LOG_DIR, "upload_manager.log"), maxBytes=1_000_000, backupCount=2, encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(fh)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(sh)

def upload_and_prune(out_dir: str, hours_gate: bool = True) -> str:
    """
    hours_gate=True 時只允許 06:00/14:00 上傳（台北時間）。
    現在為 stub：僅記錄動作與生成假連結。
    """
    now = datetime.utcnow() + timedelta(hours=8)
    if hours_gate and now.hour not in (6, 14):
        logger.info(f"非允許時段（{now.hour}），跳過上傳")
        return ""

    # 找到音檔
    candidates = [f for f in os.listdir(out_dir) if f.endswith((".mp3",".wav"))]
    if not candidates:
        logger.warning("找不到音訊檔，跳過上傳")
        return ""

    # 假連結
    link = f"https://example.com/{os.path.basename(out_dir)}/{candidates[0]}"
    with open(os.path.join(out_dir, "archive_audio_url.txt"), "w", encoding="utf-8") as f:
        f.write(link)
    logger.info(f"上傳完成（stub），連結：{link}")

    # 清除 14 天前的本地檔案（僅示意）
    # 真正 B2 刪除：可用 b2sdk 在這裡實作
    return link