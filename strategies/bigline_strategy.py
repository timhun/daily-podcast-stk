import pandas as pd
import numpy as np
import ta
from loguru import logger
import os
import matplotlib.pyplot as plt
from datetime import datetime
import json
from .base_strategy import BaseStrategy
from .utils import generate_performance_chart

class BigLineStrategy(BaseStrategy):
    def __init__(self, config, params=None):
        super().__init__(config, params)
        if not params:
            try:
                with open('strategies/bigline_strategy.json', 'r', encoding='utf-8') as f:
                    self.params = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.error(f"載入 bigline_strategy.json 失敗: {str(e)}，使用預設參數")
                self.params = {
                    "weights": [[0.4, 0.35, 0.25], [0.5, 0.3, 0.2], [0.3, 0.4, 0.3]],
                    "ma_short": 5,
                    "ma_mid": 20,
                    "ma_long": 60,
                    "vol_window": 60,
                    "rsi_window": 14
                }

    def backtest(self, symbol, data, timeframe='daily'):
        #logger.info(f"開始回測 BigLine 策略: {symbol}, 時間框架: {timeframe}")
        
        if symbol not in ['QQQ', '0050.TW']:
            #logger.info(f"{symbol} 非主要交易標的，跳過回測")
            return self._default_results()

        def _first(value, fallback):
            if value is None:
                return fallback
            if isinstance(value, list):
                return value[0]
            return value

        df = data.copy()
        if 'date' not in df.columns:
            if df.index.name == 'date':
                df = df.reset_index()  # Reset if already indexed
            else:
                logger.error(f"{symbol} 數據缺少 'date' 欄位或索引")
                return self._default_results()

        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        if hasattr(df['date'], 'dt'):
            try:
                df['date'] = df['date'].dt.tz_localize(None)
            except TypeError:
                pass
        df = df.dropna(subset=['date']).sort_values('date')
        if df.empty:
            logger.error(f"{symbol} 缺少有效日期資料")
            return self._default_results()
        df.set_index('date', inplace=True, drop=False)
        
        index_symbol = '^TWII' if symbol == '0050.TW' else '^IXIC'
        index_file_path = f"{self.config['data_paths']['market']}/{timeframe}_{index_symbol.replace('^', '').replace('.', '_')}.csv"
        
        if not os.path.exists(index_file_path):
            logger.error(f"大盤 {index_symbol} {timeframe} 歷史數據檔案不存在")
            return self._default_results()
        
        try:
            index_df = pd.read_csv(index_file_path)
            index_df['date'] = pd.to_datetime(index_df['date'], errors='coerce')
            if hasattr(index_df['date'], 'dt'):
                try:
                    index_df['date'] = index_df['date'].dt.tz_localize(None)
                except TypeError:
                    pass
            index_df = index_df.dropna(subset=['date']).sort_values('date')
            ma_short_window = int(_first(self.params.get('ma_short'), 5))
            ma_mid_window = int(_first(self.params.get('ma_mid'), 20))
            ma_long_window = int(_first(self.params.get('ma_long'), 60))
            vol_window = int(_first(self.params.get('vol_window'), 60))
            rsi_window = int(_first(self.params.get('rsi_window'), 14))

            if df.empty or len(df) < ma_long_window or index_df.empty or len(index_df) < ma_long_window:
                logger.error(f"{symbol} 或大盤 {index_symbol} {timeframe} 數據不足")
                return self._default_results()

            index_df = index_df.set_index('date')
            df = df.join(index_df[['close', 'volume']], rsuffix='_index', how='inner')
            if df.empty or len(df) < ma_long_window:
                logger.error(f"{symbol} 與大盤 {index_symbol} 對齊後數據不足")
                return self._default_results()

            prices = df['close']
            volume = df['volume']
            index_prices = df['close_index']
            if 'sentiment_score' in df.columns:
                sentiment_score = df['sentiment_score']
            else:
                sentiment_score = pd.Series(0.0, index=df.index, name='sentiment_score')
                df['sentiment_score'] = sentiment_score
            
            weights_raw = self.params.get('weights', [0.4, 0.35, 0.25])
            weights = weights_raw if isinstance(weights_raw, list) and not isinstance(weights_raw[0], list) else _first(weights_raw, [0.4, 0.35, 0.25])
            
            ma_short = prices.rolling(window=ma_short_window).mean()
            ma_mid = prices.rolling(window=ma_mid_window).mean()
            ma_long = prices.rolling(window=ma_long_window).mean()
            bullish = (ma_short > ma_mid) & (ma_mid > ma_long)
            
            big_line = (weights[0] * ma_short + weights[1] * ma_mid + weights[2] * ma_long)
            
            max_vol = volume.rolling(window=vol_window).max()
            vol_factor = 1 + (volume / (max_vol + 1e-9)) / 1e6
            big_line_weighted = big_line * vol_factor
            big_line_diff = big_line_weighted.diff()
            
            index_ma_short = index_prices.rolling(window=ma_short_window).mean()
            index_ma_mid = index_prices.rolling(window=ma_mid_window).mean()
            index_ma_long = index_prices.rolling(window=ma_long_window).mean()
            index_bullish = (index_ma_short > index_ma_mid) & (index_ma_mid > index_ma_long)
            index_rsi = ta.momentum.RSIIndicator(index_prices, window=rsi_window).rsi()
            
            df['signal'] = 0
            df.loc[(big_line_diff > 0) & bullish & index_bullish & (index_rsi < 70) & (sentiment_score > 0.0), 'signal'] = 1
            df.loc[(big_line_diff < 0) & ~index_bullish & (index_rsi > 30) & (sentiment_score < 0.0), 'signal'] = -1
            
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
            
            generate_performance_chart(df, symbol, timeframe)
            
            logger.info(f"{symbol} signal distribution: {df['signal'].value_counts().to_dict()}")
            logger.info(f"{symbol} returns std: {df['strategy_returns'].std():.4f}")
            
            return {
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'expected_return': expected_return,
                'signals': signals
            }
        except Exception as e:
            #logger.error(f"{symbol} {timeframe} 回測失敗: {str(e)}")
            return self._default_results()

    def _load_sentiment_score(self, symbol, timeframe):
        # Placeholder for sentiment score loading (as in original)
        return 0.0  # Replace with actual sentiment loading logic if needed

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
