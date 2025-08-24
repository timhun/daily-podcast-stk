"""
工具函數模組
提供日誌、配置管理、錯誤處理等基礎功能
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz
from loguru import logger
from typing import Dict, Any, Optional, Union
import time
import functools


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.base_config = self.load_json("base_config.json")
        self.strategies_config = self.load_json("strategies.json")
        self.secrets = self.load_secrets()
    
    def load_json(self, filename: str) -> Dict[str, Any]:
        """載入 JSON 配置檔案"""
        file_path = self.config_dir / filename
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"配置檔案不存在: {file_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"配置檔案格式錯誤: {file_path}, 錯誤: {e}")
            return {}
    
    def load_secrets(self) -> Dict[str, Any]:
        """載入密鑰配置（優先使用環境變數）"""
        secrets = {}
        
        # 從環境變數載入
        env_mapping = {
            'GROK_API_KEY': ['api_keys', 'grok_api_key'],
            'OPENAI_API_KEY': ['api_keys', 'openai_api_key'],
            'B2_KEY_ID': ['cloud_storage', 'b2_key_id'],
            'B2_APPLICATION_KEY': ['cloud_storage', 'b2_application_key'],
            'B2_BUCKET_NAME': ['cloud_storage', 'b2_bucket_name'],
            'SLACK_BOT_TOKEN': ['notifications', 'slack_bot_token'],
            'SLACK_CHANNEL': ['notifications', 'slack_channel'],
        }
        
        for env_key, json_path in env_mapping.items():
            value = os.getenv(env_key)
            if value:
                # 建立巢狀字典結構
                current = secrets
                for key in json_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[json_path[-1]] = value
        
        # 如果環境變數不存在，嘗試從 secrets.json 載入
        if not secrets:
            secrets_file = self.config_dir / "secrets.json"
            if secrets_file.exists():
                secrets = self.load_json("secrets.json")
        
        return secrets
    
    def get(self, path: str, default: Any = None) -> Any:
        """使用點記號路徑獲取配置值"""
        keys = path.split('.')
        config = self.base_config
        
        for key in keys:
            if isinstance(config, dict) and key in config:
                config = config[key]
            else:
                return default
        
        return config
    
    def get_secret(self, path: str, default: Any = None) -> Any:
        """獲取密鑰配置"""
        keys = path.split('.')
        config = self.secrets
        
        for key in keys:
            if isinstance(config, dict) and key in config:
                config = config[key]
            else:
                return default
        
        return config


class LoggerSetup:
    """日誌系統設定"""
    
    @staticmethod
    def setup_logger(module_name: str, log_level: str = "INFO") -> None:
        """設定模組專用日誌"""
        
        # 移除預設處理器
        logger.remove()
        
        # 創建日誌目錄
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 控制台輸出格式
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        
        # 檔案輸出格式
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} | {message}"
        )
        
        # 添加控制台處理器
        logger.add(
            sys.stdout,
            format=console_format,
            level=log_level,
            colorize=True
        )
        
        # 添加檔案處理器
        logger.add(
            log_dir / f"{module_name}.log",
            format=file_format,
            level=log_level,
            rotation="1 day",
            retention="7 days",
            compression="zip"
        )
        
        # 添加錯誤專用檔案
        logger.add(
            log_dir / f"{module_name}_errors.log",
            format=file_format,
            level="ERROR",
            rotation="1 week",
            retention="30 days"
        )


def retry_on_failure(max_retries: int = 3, delay: float = 3.0, backoff_factor: float = 2.0):
    """
    裝飾器：失敗時自動重試
    
    Args:
        max_retries: 最大重試次數
        delay: 初始延遲時間（秒）
        backoff_factor: 延遲時間倍增因子
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(f"{func.__name__} 重試成功，第 {attempt + 1} 次嘗試")
                    return result
                
                except Exception as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} 重試失敗，已達最大重試次數 {max_retries}")
                        break
                    
                    logger.warning(
                        f"{func.__name__} 第 {attempt + 1} 次嘗試失敗: {str(e)}, "
                        f"{current_delay:.1f}秒後重試"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
            raise last_exception
        
        return wrapper
    return decorator


def get_taiwan_time() -> datetime:
    """獲取台灣時間"""
    tw_tz = pytz.timezone('Asia/Taipei')
    return datetime.now(tw_tz)


def is_market_open(market: str = 'taiwan') -> bool:
    """
    檢查市場是否開放
    
    Args:
        market: 'taiwan' 或 'us'
    """
    config = ConfigManager()
    tw_time = get_taiwan_time()
    
    # 週末不開盤
    if tw_time.weekday() >= 5:  # 週六=5, 週日=6
        return False
    
    if market == 'taiwan':
        # 台股開盤時間：09:00-13:30 (台北時間)
        market_open = tw_time.replace(hour=9, minute=0, second=0, microsecond=0)
        market_close = tw_time.replace(hour=13, minute=30, second=0, microsecond=0)
        return market_open <= tw_time <= market_close
    
    elif market == 'us':
        # 美股開盤時間：22:30-05:00 (台北時間，夏令時間可能不同)
        # 這裡簡化處理，實際應考慮夏令時間
        if tw_time.hour >= 22 or tw_time.hour <= 5:
            return True
        return False
    
    return False


def validate_data_quality(data, symbol: str, min_rows: int = 10) -> bool:
    """
    驗證數據品質
    
    Args:
        data: pandas DataFrame
        symbol: 股票代號
        min_rows: 最小資料行數
    """
    if data is None or len(data) < min_rows:
        logger.warning(f"{symbol} 數據行數不足: {len(data) if data is not None else 0}")
        return False
    
    # 檢查必要欄位
    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing_columns = [col for col in required_columns if col not in data.columns]
    
    if missing_columns:
        logger.warning(f"{symbol} 缺少必要欄位: {missing_columns}")
        return False
    
    # 檢查空值比例
    null_percentage = data.isnull().sum().sum() / (len(data) * len(data.columns))
    if null_percentage > 0.1:  # 超過10%空值
        logger.warning(f"{symbol} 空值比例過高: {null_percentage:.2%}")
        return False
    
    # 檢查異常值（價格為0或負數）
    if (data['Close'] <= 0).any():
        logger.warning(f"{symbol} 存在異常價格數據")
        return False
    
    logger.info(f"{symbol} 數據品質驗證通過，共 {len(data)} 筆記錄")
    return True


# 全域配置管理器實例
config_manager = ConfigManager()
