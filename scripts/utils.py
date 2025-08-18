# scripts/utils.py
import logging
import pytz
from datetime import datetime

# 台灣時區
TW_TZ = pytz.timezone("Asia/Taipei")

# symbol -> benchmark 對照
BENCHMARK_MAP = {
    "0050.TW": "^TWII",   # 台股
    "QQQ": "^IXIC"        # 美股 (NASDAQ Composite)
}

def now_tw_str(fmt="%Y-%m-%d %H:%M:%S"):
    """取得台灣時間字串"""
    return datetime.now(TW_TZ).strftime(fmt)

def setup_logger(name):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger(name)
