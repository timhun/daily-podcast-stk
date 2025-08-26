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
import logging
import requests
from openai import OpenAI

def get_clean_symbol(symbol: str) -> str:
    """統一的股票代號清理函數"""
    return symbol.replace('^', '').replace('.', '_').replace('=', '_').replace('-', '_')

class ConfigManager:
    def __init__(self, config_dir: str = "config"):
        # 使用更可靠的路徑解析
        if os.getenv("GITHUB_WORKSPACE"):
            # 在 GitHub Actions 中
            project_root = Path(os.getenv("GITHUB_WORKSPACE"))
            logger.info(f"檢測到 GitHub Actions 環境，項目根目錄: {project_root}")
        elif os.getenv("PYTHONPATH"):
            # 如果設置了 PYTHONPATH，使用第一個路徑
            python_paths = os.getenv("PYTHONPATH").split(os.pathsep)
            project_root = Path(python_paths[0]) if python_paths else Path.cwd()
            logger.info(f"使用 PYTHONPATH 中的項目根目錄: {project_root}")
        else:
            # 本地執行時，從當前檔案位置推導
            current_file = Path(__file__).resolve()
            if current_file.parent.name == "scripts":
                project_root = current_file.parent.parent
            else:
                project_root = Path.cwd()
            logger.info(f"本地執行，推導項目根目錄: {project_root}")
        
        self.config_dir = project_root / config_dir
        self.project_root = project_root
        
        logger.info(f"配置目錄路徑: {self.config_dir.absolute()}")
        logger.info(f"項目根目錄: {self.project_root.absolute()}")
        
        # 檢查配置目錄是否存在
        if not self.config_dir.exists():
            logger.error(f"配置目錄不存在: {self.config_dir}")
            # 嘗試常見的備用位置
            alternative_paths = [
                Path.cwd() / config_dir,
                Path(__file__).parent / config_dir,
                Path(__file__).parent.parent / config_dir
            ]
            
            for alt_path in alternative_paths:
                if alt_path.exists():
                    logger.info(f"找到備用配置目錄: {alt_path}")
                    self.config_dir = alt_path
                    break
            else:
                logger.warning(f"所有配置目錄都不存在，將使用默認配置")
        
        self.base_config = self.load_json("base_config.json")
        self.strategies_config = self.load_json("strategies.json")
        self.secrets = self.load_secrets()
        
        # 調試信息
        logger.info(f"已載入配置 - base_config keys: {list(self.base_config.keys()) if self.base_config else 'None'}")
        if self.base_config and "markets" in self.base_config:
            taiwan_symbols = self.base_config.get("markets", {}).get("taiwan", {}).get("symbols", {}).get("daily", [])
            logger.info(f"台股股票列表: {taiwan_symbols}")

    def load_json(self, filename: str) -> Dict[str, Any]:
        """載入 JSON 配置檔案"""
        file_path = self.config_dir / filename
        try:
            logger.debug(f"嘗試載入配置檔案: {file_path.absolute()}")
            
            if not file_path.exists():
                logger.warning(f"配置檔案不存在: {file_path.absolute()}")
                return self._get_default_config(filename)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.success(f"成功載入配置檔案: {filename}")
                return config
                
        except FileNotFoundError:
            logger.warning(f"配置檔案不存在: {file_path}")
            return self._get_default_config(filename)
        except json.JSONDecodeError as e:
            logger.error(f"配置檔案格式錯誤: {file_path}, 錯誤: {e}")
            return self._get_default_config(filename)
        except Exception as e:
            logger.error(f"載入配置檔案時發生錯誤: {file_path}, 錯誤: {e}")
            return self._get_default_config(filename)

    def _get_default_config(self, filename: str) -> Dict[str, Any]:
        """獲取默認配置"""
        if filename == "base_config.json":
            return {
                "system": {
                    "timezone": "Asia/Taipei",
                    "log_level": "INFO",
                    "max_retries": 3,
                    "retry_delay": 3.0,
                    "backoff_factor": 2.0
                },
                "markets": {
                    "taiwan": {
                        "symbols": {
                            "daily": ["^TWII", "0050.TW", "2330.TW"],
                            "hourly": ["0050.TW"]
                        },
                        "news_sources": []
                    },
                    "us": {
                        "symbols": {
                            "daily": ["^GSPC", "QQQ", "SPY"],
                            "hourly": ["QQQ"]
                        },
                        "news_sources": []
                    },
                    "crypto": {
                        "symbols": {
                            "daily": ["BTC-USD", "ETH-USD"],
                            "hourly": []
                        }
                    }
                },
                "data_collection": {
                    "daily_history_days": 300,
                    "hourly_history_days": 14,
                    "data_retention_days": 30,
                    "news_limit": 5
                },
                "notifications": {
                    "slack_webhook_url": ""
                }
            }
        elif filename == "strategies.json":
            return {
                "available_strategies": {
                    "technical_analysis": {
                        "name": "技術分析策略",
                        "enabled": True,
                        "parameters": {
                            "sma_short": 20,
                            "sma_long": 50,
                            "rsi_period": 14,
                            "rsi_overbought": 70,
                            "rsi_oversold": 30
                        },
                        "weight": 0.25
                    }
                }
            }
        else:
            return {}

    def get(self, path: str, default: Any = None) -> Any:
        """使用點記號路徑獲取配置值"""
        keys = path.split('.')
        config = self.base_config
        
        for key in keys:
            if isinstance(config, dict) and key in config:
                config = config[key]
            else:
                logger.debug(f"配置路徑 {path} 不存在，返回默認值: {default}")
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
                logger.debug(f"密鑰路徑 {path} 不存在，返回默認值")
                return default
        
        return config

    def get_data_path(self, relative_path: str = "") -> Path:
        """獲取數據目錄的絕對路徑"""
        data_path = self.project_root / "data"
        if relative_path:
            data_path = data_path / relative_path
        return data_path

    def get_log_path(self, relative_path: str = "") -> Path:
        """獲取日誌目錄的絕對路徑"""
        log_path = self.project_root / "logs"
        if relative_path:
            log_path = log_path / relative_path
        return log_path

class LoggerSetup:
    """日誌系統設定"""
    _initialized_loggers = set()

    @staticmethod
    def setup_logger(module_name: str, log_level: str = "INFO") -> None:
        """設定模組專用日誌"""
        from loguru import logger
        
        # 避免重複初始化同一個模組的日誌
        if module_name in LoggerSetup._initialized_loggers:
            return logger.bind(module=module_name)
        
        # 移除預設處理器（只在第一次調用時）
        if not LoggerSetup._initialized_loggers:
            logger.remove()
        
        # 創建日誌目錄
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 控制台輸出格式
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[module]}</cyan> | "
            "<level>{message}</level>"
        )
        
        # 檔案輸出格式
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{extra[module]} | {message}"
        )
        
        # 添加控制台處理器（只在第一次調用時）
        if not LoggerSetup._initialized_loggers:
            logger.add(
                sys.stdout,
                format=console_format,
                level=log_level,
                colorize=True,
                filter=lambda record: record["extra"].get("module") == module_name
            )
        
        # 添加檔案處理器
        logger.add(
            log_dir / f"{module_name}.log",
            format=file_format,
            level=log_level,
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            filter=lambda record: record["extra"].get("module") == module_name
        )
        
        # 綁定模組名稱到 logger 並返回
        bound_logger = logger.bind(module=module_name)
        LoggerSetup._initialized_loggers.add(module_name)
        return bound_logger

def slack_alert(message: str, channel: Optional[str] = None, urgent: bool = False):
    """發送 Slack 通知 (使用 webhook)"""
    # 嘗試多種方式獲取 webhook URL
    webhook_url = None
    if config_manager:
        webhook_url = (
            config_manager.get_secret('notifications.slack_webhook_url') or
            config_manager.get('notifications.slack_webhook_url')
        )

    if not webhook_url:
        webhook_url = os.getenv('SLACK_WEBHOOK_URL')

    if not webhook_url:
        logger.warning("未配置 Slack Webhook URL，跳過通知發送")
        logger.info(f"通知內容: {message}")
        return

    try:
        # 格式化訊息
        timestamp = get_taiwan_time().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"🤖 *策略管理系統通知* ({timestamp})\n{message}"
        if urgent:
            formatted_message = f"🚨 **緊急** {formatted_message}"
        
        # 發送到 Slack
        payload = {
            "text": formatted_message,
            "username": "數據收集智士",
            "icon_emoji": ":robot_face:"
        }
        
        if channel:
            payload["channel"] = channel
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        
        logger.info("Slack 通知發送成功")
        
    except requests.RequestException as e:
        logger.error(f"發送 Slack 通知時發生網路錯誤: {e}")
    except Exception as e:
        logger.error(f"發送 Slack 通知時發生錯誤: {e}")

    # 無論如何都在日誌中記錄訊息
    logger.info(f"通知內容: {message}")

def retry_on_failure(max_retries: int = 3, delay: float = 3.0, backoff_factor: float = 2.0):
    """裝飾器：失敗時自動重試"""
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
    """檢查市場是否開放"""
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
    """驗證數據品質"""
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

    # 檢查價格數據的合理性（High >= Low, Close 在 High-Low 範圍內）
    if (data['High'] < data['Low']).any():
        logger.warning(f"{symbol} 存在 High < Low 的異常數據")
        return False

    if ((data['Close'] > data['High']) | (data['Close'] < data['Low'])).any():
        logger.warning(f"{symbol} 存在 Close 超出 High-Low 範圍的異常數據")
        return False

    logger.debug(f"{symbol} 數據品質驗證通過，共 {len(data)} 筆記錄")
    return True

def safe_file_operation(operation):
    """安全的檔案操作裝飾器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except FileNotFoundError as e:
                logger.error(f"檔案不存在: {e}")
                return None
            except PermissionError as e:
                logger.error(f"檔案權限錯誤: {e}")
                return None
            except OSError as e:
                logger.error(f"檔案系統錯誤: {e}")
                return None
            except Exception as e:
                logger.error(f"檔案操作時發生未預期錯誤: {e}")
                return None
        return wrapper
    return decorator

def format_number(num: float, decimals: int = 2) -> str:
    """格式化數字顯示"""
    if abs(num) >= 1_000_000:
        return f"{num/1_000_000:.{decimals}f}M"
    elif abs(num) >= 1_000:
        return f"{num/1_000:.{decimals}f}K"
    else:
        return f"{num:.{decimals}f}"

def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """計算百分比變化"""
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / abs(old_value)) * 100

def get_trading_day_offset(days: int) -> datetime:
    """獲取交易日偏移（排除週末）"""
    current = get_taiwan_time()
    count = 0

    while count < abs(days):
        if days > 0:
            current += timedelta(days=1)
        else:
            current -= timedelta(days=1)
        
        # 跳過週末
        if current.weekday() < 5:  # Monday=0, Sunday=6
            count += 1

    return current

# 全域配置管理器實例
try:
    config_manager = ConfigManager()
    logger.info("配置管理器初始化成功")
except Exception as e:
    logger.error(f"配置管理器初始化失敗: {e}")
    class DummyConfigManager:
        def __init__(self):
            self.base_config = {}
            self.strategies_config = {}
            self.secrets = {}

        def get(self, path, default=None):
            return default

        def get_secret(self, path, default=None):
            return default

        def get_data_path(self, relative_path=""):
            return Path("data") / relative_path

    config_manager = DummyConfigManager()
    logger.warning("使用空的配置管理器作為後備")