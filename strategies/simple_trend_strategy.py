import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
from loguru import logger
import json

class SimpleTrendStrategy(BaseStrategy):
    def __init__(self, config, params=None):
        super().__init__(config, params)
        if not params:
            try:
                with open('strategies/simple_trend_strategy.json', 'r', encoding='utf-8') as f:
                    self.params = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.error(f"載入 simple_trend_strategy.json 失敗: {str(e)}，使用預設參數")
                self.params = {
                    "ma_window": 20,
                    "vol_window": 20,
                    "breakout_price": 53.0,  # 預設突破價格，可根據標的調整
                    "min_data_length": 20
                }

    def backtest(self, symbol, data, timeframe='weekly'):
        df = self.load_data(symbol, timeframe)
        if df is None:
            return self._default_results()

        try:
            # 計算移動平均線
            df['MA'] = df['close'].rolling(window=self.params['ma_window']).mean()

            # 確認趨勢
            df['Trend_OK'] = (df['close'] > df['MA']) & (df['MA'] > df['MA'].shift(1))

            # 觀察量能
            df['Vol_Mean'] = df['volume'].rolling(window=self.params['vol_window']).mean()
            df['Vol_OK'] = (df['volume'] > df['Vol_Mean']) & (df['close'] > df['open'])

            # 突破進場
            df['Breakout_OK'] = df['close'] > self.params['breakout_price']

            # 結合判斷並給出買賣信號
            df['signal'] = 0
            df.loc[df['Trend_OK'] & df['Vol_OK'] & df['Breakout_OK'], 'signal'] = 1  # 買入
            df.loc[df['close'] < df['MA'], 'signal'] = -1  # 賣出

            # 計算回報
            df['returns'] = df['close'].pct_change()
            df['strategy_returns'] = df['returns'] * df['signal'].shift(1)

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

            return {
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'expected_return': expected_return,
                'signals': signals
            }
        except Exception as e:
            logger.error(f"{symbol} {timeframe} 回測失敗: {str(e)}")
            return self._default_results()
