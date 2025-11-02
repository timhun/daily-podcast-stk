import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from loguru import logger
from .base_strategy import BaseStrategy
from .utils import generate_performance_chart
import json

class GodSystemStrategy(BaseStrategy):
    def __init__(self, config, params=None):
        super().__init__(config, params)
        if not params:
            try:
                with open('strategies/god_system_strategy.json', 'r', encoding='utf-8') as f:
                    self.params = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.error(f"載入 god_system_strategy.json 失敗: {str(e)}，使用預設參數")
                self.params = {
                    "ma_month": 20  # 月均線窗口
                }

    def backtest(self, symbol, data, timeframe='daily'):
        logger.info(f"開始回測 God System 策略: {symbol}, 時間框架: {timeframe}")
        
        if symbol not in ['^TWII']:
            logger.info(f"{symbol} 非主要交易標的，跳過回測")
            return self._default_results()

        if not all(col in data for col in ['close']) or data.empty:
            logger.error(f"{symbol} 數據缺少必要欄位或為空")
            return self._default_results()

        df = data.copy()
        prices = df['close']

        # 計算月均線 (20 日均線)
        ma_month = prices.rolling(window=self.params['ma_month']).mean()

        # 產生訊號：收盤價 > 月均線 -> LONG, < 月均線 -> SHORT, 相等 -> NEUTRAL
        df['signal'] = 0
        df.loc[prices > ma_month, 'signal'] = 1   # LONG
        df.loc[prices < ma_month, 'signal'] = -1  # SHORT
        df.loc[prices == ma_month, 'signal'] = 0  # NEUTRAL

        # 計算回報
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['returns'] * df['signal'].shift(1)

        # 計算績效指標
        sharpe_ratio = df['strategy_returns'].mean() / df['strategy_returns'].std() * np.sqrt(
            self.config['strategy_params']['sharpe_annualization_daily'] if timeframe == 'daily' else self.config['strategy_params']['sharpe_annualization_hourly']
        ) if df['strategy_returns'].std() != 0 else 0
        sharpe_ratio = sharpe_ratio if not np.isnan(sharpe_ratio) else 0

        cum_returns = df['strategy_returns'].cumsum()
        max_drawdown = (cum_returns.cummax() - cum_returns).max()
        max_drawdown = max_drawdown if not np.isnan(max_drawdown) else 0

        expected_return = df['strategy_returns'].mean() * (
            self.config['strategy_params']['expected_return_annualization_daily'] if timeframe == 'daily' else self.config['strategy_params']['expected_return_annualization_hourly']
        )
        expected_return = expected_return if not np.isnan(expected_return) else 0

        latest_close = df['close'].iloc[-1]
        multiplier = self.config['strategy_params']['daily_multiplier'] if timeframe == 'daily' else self.config['strategy_params']['hourly_multiplier']
        signals = {
            'position': 'LONG' if df['signal'].iloc[-1] == 1 else 'SHORT' if df['signal'].iloc[-1] == -1 else 'NEUTRAL',
            'entry_price': latest_close,
            'target_price': latest_close * multiplier,
            'stop_loss': latest_close * self.config['strategy_params']['stop_loss_ratio'],
            'position_size': self.config['strategy_params']['position_size']
        }

        # 生成績效圖表
        generate_performance_chart(df, symbol, timeframe)

        logger.info(f"{symbol} 信號分佈: {df['signal'].value_counts().to_dict()}")
        logger.info(f"{symbol} 回報標準差: {df['strategy_returns'].std():.4f}")

        return {
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'expected_return': expected_return,
            'signals': signals
        }

    def _default_results(self):
        return {
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'expected_return': 0,
            'signals': {
                'position': 'NEUTRAL',
                'entry_price': 0.0,
                'target_price': 0.0,
                'stop_loss': 0.0,
                'position_size': 0.0
            }
        }
