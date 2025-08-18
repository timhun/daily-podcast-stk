# scripts/utils.py
import json
import os
import logging
import pytz
from datetime import datetime

logger = logging.getLogger("utils")

# 預設路徑
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")

def load_config(config_path: str = CONFIG_PATH) -> dict:
    """讀取 config.json，失敗則拋出例外"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"找不到設定檔 {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config

def get_symbols(config: dict) -> list:
    """回傳所有要追蹤的 symbols"""
    return config.get("symbols", [])

def get_benchmark(symbol: str, config: dict) -> str:
    """根據 symbol 找 benchmark"""
    bm_map = config.get("settings", {}).get("benchmark_map", {})
    return bm_map.get(symbol)

def get_timezone(config: dict):
    """回傳設定的時區物件"""
    tz_name = config.get("settings", {}).get("time_zone", "Asia/Taipei")
    return pytz.timezone(tz_name)

def now_local(config: dict) -> datetime:
    """取得當地時間"""
    tz = get_timezone(config)
    return datetime.now(tz)
