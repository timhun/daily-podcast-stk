#strategies/bigline_strategy.py
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
        logger.info(f"開始回測 BigLine 策略: {symbol}, 時間框架: {timeframe}")
        
        if symbol not in ['QQQ', '0050.TW']:
            logger.info(f"{symbol} 非主要交易標的，跳過回測")
            return self._default_results()

        required_columns = ['open', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            logger.error(f"{symbol} 缺少必要欄位: {missing_columns}, 實際欄位: {list(data.columns)}, 數據長度: {len(data)}")
            return self._default_results()

        df = data.copy()
        index_symbol = '^TWII' if symbol == '0050.TW' else '^IXIC'
        index_file_path = f"{self.config['data_paths']['market']}/{timeframe}_{index_symbol.replace('^', '').replace('.', '_')}.csv"
        
        if not os.path.exists(index_file_path):
            logger.error(f"大盤 {index_symbol} {timeframe} 歷史數據檔案不存在")
            return self._default_results()
        
        try:
            index_df = pd.read_csv(index_file_path)
            index_df['date'] = pd.to_datetime(index_df['date'])
            if df.empty or len(df) < self.params['ma_long'] or index_df.empty or len(index_df) < self.params['ma_long']:
                logger.error(f"{symbol} 或大盤 {index_symbol} {timeframe} 數據不足")
                return self._default_results()
            
            df = df.sort_values('date').set_index('date')
            index_df = index_df.sort_values('date').set_index('date')
            df = df.join(index_df[['close', 'volume']], rsuffix='_index', how='inner')
            
            prices = df['close']
            volume = df['volume']
            index_prices = df['close_index']
            sentiment_score = df['sentiment_score']
            
            weights = self.params['weights'] if isinstance(self.params['weights'], list) and not isinstance(self.params['weights'][0], list) else self.params['weights'][0]
            
            ma_short = prices.rolling(window=self.params['ma_short']).mean()
            ma_mid = prices.rolling(window=self.params['ma_mid']).mean()
            ma_long = prices.rolling(window=self.params['ma_long']).mean()
            bullish = (ma_short > ma_mid) & (ma_mid > ma_long)
            
            big_line = (weights[0] * ma_short + weights[1] * ma_mid + weights[2] * ma_long)
            
            max_vol = volume.rolling(window=self.params['vol_window']).max()
            vol_factor = 1 + (volume / (max_vol + 1e-9)) / 1e6
            big_line_weighted = big_line * vol_factor
            big_line_diff = big_line_weighted.diff()
            
            index_ma_short = index_prices.rolling(window=self.params['ma_short']).mean()
            index_ma_mid = index_prices.rolling(window=self.params['ma_mid']).mean()
            index_ma_long = index_prices.rolling(window=self.params['ma_long']).mean()
            index_bullish = (index_ma_short > index_ma_mid) & (index_ma_mid > index_ma_long)
            index_rsi = ta.momentum.RSIIndicator(index_prices, window=self.params['rsi_window']).rsi()
            
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
            logger.error(f"{symbol} {timeframe} 回測失敗: {str(e)}")
            return self._default_results()

    def _load_sentiment_score(self, symbol, timeframe):
        sentiment_file = f"{self.config['data_paths']['sentiment']}/{datetime.today().strftime('%Y-%m-%d')}/social_metrics.json"
        try:
            with open(sentiment_file, 'r', encoding='utf-8') as f:
                sentiment_data = json.load(f)
            return sentiment_data.get('symbols', {}).get(symbol, {}).get('sentiment_score', 0.0)
        except Exception as e:
            logger.error(f"載入情緒數據失敗: {str(e)}")
            return 0.0

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
