import pandas as pd
import numpy as np
import os
from loguru import logger

class BaseStrategy:
    def __init__(self, config, params=None):
        self.config = config
        self.params = params or {}
        self.min_data_length = self.params.get('min_data_length_rsi_sma', 20)

    def load_data(self, symbol, timeframe='daily'):
        file_path = f"{self.config['data_paths']['market']}/{timeframe}_{symbol.replace('^', '').replace('.', '_')}.csv"
        if not os.path.exists(file_path):
            logger.error(f"{symbol} {timeframe} 歷史數據檔案不存在: {file_path}")
            return None
        try:
            df = pd.read_csv(file_path)
            df['date'] = pd.to_datetime(df['date'])
            if df.empty or len(df) < self.min_data_length:
                logger.error(f"{symbol} {timeframe} 數據不足: 實際 {len(df)} 筆，需 {self.min_data_length} 筆")
                return None
            return df
        except Exception as e:
            logger.error(f"{symbol} 數據載入失敗: {str(e)}")
            return None

    def backtest(self, symbol, data, timeframe='daily'):
        raise NotImplementedError("Subclasses must implement backtest method")

    def _default_results(self):
        return {
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'expected_return': 0,
            'signals': {}
        }
