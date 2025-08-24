"""
工具函數模組
提供日誌、配置管理、錯誤處理等基礎功能
"""

import json
import os
from pathlib import Path
from datetime import datetime
import pytz
import logging
from typing import Dict, Any, Optional
import time
import functools
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import pandas as pd

def setup_json_logger(name: str) -> logging.Logger:
    """設置 JSON 格式的日誌"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    handler = logging.FileHandler(f"logs/{name}.json", mode='a', encoding='utf-8')
    formatter = logging.Formatter('{"time": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": %(message)s}')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # Add console handler for debugging
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = "config.json", strategies_path: str = "strategies.json"):
        self.config_path = Path(config_path)
        self.strategies_path = Path(strategies_path)
        self.config = self.load_json(self.config_path)
        self.strategies = self.load_json(self.strategies_path)
    
    def load_json(self, file_path: Path) -> Dict[str, Any]:
        """載入 JSON 配置檔案"""
        logger = setup_json_logger('utils')
        try:
            if not file_path.exists():
                error_msg = f"配置檔案不存在: {file_path}"
                logger.error(json.dumps({"error": error_msg}))
                slack_alert(error_msg)
                raise FileNotFoundError(error_msg)
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(json.dumps({"file": str(file_path), "status": "loaded"}))
                return data
        except json.JSONDecodeError as e:
            error_msg = f"配置檔案格式錯誤: {file_path}, 錯誤: {e}"
            logger.error(json.dumps({"error": error_msg}))
            slack_alert(error_msg)
            raise
    
    def get(self, path: str, default: Any = None) -> Any:
        """使用點記號路徑獲取配置值"""
        logger = setup_json_logger('utils')
        keys = path.split('.')
        config = self.config
        for key in keys:
            if isinstance(config, dict) and key in config:
                config = config[key]
            else:
                logger.warning(json.dumps({"path": path, "status": "not found", "default": default}))
                return default
        return config
    
    def get_strategy(self, path: str, default: Any = None) -> Any:
        """獲取策略配置"""
        logger = setup_json_logger('utils')
        keys = path.split('.')
        config = self.strategies
        for key in keys:
            if isinstance(config, dict) and key in config:
                config = config[key]
            else:
                logger.warning(json.dumps({"path": path, "status": "not found", "default": default}))
                return default
        return config

def retry_on_failure(max_retries: int = 3, delay: float = 3.0, backoff_factor: float = 2.0):
    """
    裝飾器：失敗時自動重試
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = setup_json_logger('utils')
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(json.dumps({"function": func.__name__, "attempt": attempt + 1, "status": "success"}))
                    return result
                except Exception as e:
                    last_exception = e
                    logger.warning(json.dumps({"function": func.__name__, "attempt": attempt + 1, "error": str(e)}))
                    if attempt == max_retries - 1:
                        error_msg = f"{func.__name__} 重試失敗，已達最大重試次數 {max_retries}"
                        logger.error(json.dumps({"function": func.__name__, "error": error_msg}))
                        slack_alert(error_msg)
                        raise last_exception
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
        return wrapper
    return decorator

def get_taiwan_time() -> datetime:
    """獲取台灣時間"""
    return datetime.now(pytz.timezone('Asia/Taipei'))

def slack_alert(message: str, channel: str = os.environ.get('SLACK_CHANNEL', '')):
    """發送 Slack 通知"""
    logger = setup_json_logger('utils')
    try:
        client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])
        client.chat_postMessage(channel=channel, text=message)
        logger.info(json.dumps({"slack_message": message, "status": "sent"}))
    except SlackApiError as e:
        logger.error(json.dumps({"slack_error": str(e)}))

def validate_data_quality(data: pd.DataFrame, symbol: str, min_rows: int = 10) -> bool:
    """
    驗證數據品質
    """
    logger = setup_json_logger('utils')
    if data is None or data.empty or len(data) < min_rows:
        error_msg = f"{symbol} 數據行數不足: {len(data) if data is not None else 0}"
        logger.error(json.dumps({"symbol": symbol, "error": error_msg}))
        slack_alert(error_msg)
        return False
    
    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing_columns = [col for col in required_columns if col not in data.columns]
    
    if missing_columns:
        error_msg = f"{symbol} 缺少必要欄位: {missing_columns}"
        logger.error(json.dumps({"symbol": symbol, "error": error_msg}))
        slack_alert(error_msg)
        return False
    
    null_percentage = data[required_columns].isna().sum().sum() / (len(data) * len(required_columns))
    if null_percentage > 0.1:
        error_msg = f"{symbol} 空值比例過高: {null_percentage:.2%}"
        logger.error(json.dumps({"symbol": symbol, "error": error_msg}))
        slack_alert(error_msg)
        return False
    
    if (data['Close'] <= 0).any():
        error_msg = f"{symbol} 存在異常價格數據"
        logger.error(json.dumps({"symbol": symbol, "error": error_msg}))
        slack_alert(error_msg)
        return False
    
    logger.info(json.dumps({"symbol": symbol, "status": "validated", "rows": len(data)}))
    return True

# Global ConfigManager instance
config_manager = ConfigManager()