import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from .base_strategy import BaseStrategy
from loguru import logger
import json

class MLStrategy(BaseStrategy):
    def __init__(self, config, params=None):
        super().__init__(config, params)
        if not params:
            try:
                with open('strategies/ml_strategy.json', 'r', encoding='utf-8') as f:
                    self.params = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load ml_strategy.json: {str(e)}, using default params")
                self.params = {
                    "n_estimators": 100,
                    "max_depth": 10,
                    "rsi_window": 14,
                    "macd_fast": 12,
                    "macd_slow": 26,
                    "macd_signal": 9,
                    "min_data_length": 30,
                    "return_threshold": 0.01
                }

    def backtest(self, symbol, data, timeframe='daily'):
        if data.empty or len(data) < 30:
            logger.warning(f"{symbol} data insufficient or empty")
            return self._default_results()

        try:
            required_columns = ['open', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                logger.error(f"{symbol} missing required columns: {missing_columns}")
                return self._default_results()

            df = data.copy()

            # Feature engineering
            df['RSI'] = self._calculate_rsi(df['close'], self.params['rsi_window'])
            df['MACD'] = self._calculate_macd(df['close'], self.params['macd_fast'], self.params['macd_slow'], self.params['macd_signal'])
            df['returns'] = df['close'].pct_change()

            # Create labels (1 for positive return, 0 for negative)
            df['label'] = (df['returns'].shift(-1) > self.params['return_threshold']).astype(int)
            logger.info(f"{symbol} 特徵工程前數據長度: {len(df)}")
            df = df.dropna()
            logger.info(f"{symbol} 特徵工程後數據長度: {len(df)}")

            if len(df) < 30:
                logger.warning(f"{symbol} insufficient data after feature engineering")
                return self._default_results()

            # Prepare features and labels
            features = ['RSI', 'MACD', 'volume']
            X = df[features]
            y = df['label']

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

            # Train Random Forest
            model = RandomForestClassifier(n_estimators=self.params['n_estimators'], max_depth=self.params['max_depth'], random_state=42)
            model.fit(X_train, y_train)

            # Predict
            df['prediction'] = model.predict(X)

            # Generate signals
            df['signal'] = 0
            df.loc[df['prediction'] == 1, 'signal'] = 1
            df.loc[df['prediction'] == 0, 'signal'] = -1

            # Calculate returns
            df['strategy_returns'] = df['returns'] * df['signal'].shift(1)

            # Performance metrics
            sharpe_ratio = df['strategy_returns'].mean() / df['strategy_returns'].std() * np.sqrt(
                self.config['strategy_params']['sharpe_annualization_daily'] if timeframe == 'daily' else 52
            ) if df['strategy_returns'].std() != 0 else 0
            sharpe_ratio = sharpe_ratio if not np.isnan(sharpe_ratio) else 0

            cum_returns = df['strategy_returns'].cumsum()
            max_drawdown = (cum_returns.cummax() - cum_returns).max()
            max_drawdown = max_drawdown if not np.isnan(max_drawdown) else 0

            expected_return = df['strategy_returns'].mean() * (
                self.config['strategy_params']['expected_return_annualization_daily'] if timeframe == 'daily' else 52
            )
            expected_return = expected_return if not np.isnan(expected_return) else 0

            # Generate trading signals
            latest_close = df['close'].iloc[-1]
            multiplier = self.config['strategy_params']['daily_multiplier'] if timeframe == 'daily' else 1.1
            signals = {
                'position': 'LONG' if df['signal'].iloc[-1] == 1 else 'SHORT' if df['signal'].iloc[-1] == -1 else 'NEUTRAL',
                'entry_price': latest_close,
                'target_price': latest_close * multiplier,
                'stop_loss': latest_close * self.config['strategy_params']['stop_loss_ratio'],
                'position_size': self.config['strategy_params']['position_size']
            }

            logger.info(f"{symbol} 信號分佈: {df['signal'].value_counts().to_dict()}")
            logger.info(f"{symbol} 回報標準差: {df['strategy_returns'].std():.3f}")

            return {
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'expected_return': expected_return,
                'signals': signals
            }
        except Exception as e:
            logger.error(f"{symbol} {timeframe} 回測失敗: {str(e)}")
            return self._default_results()

    def _calculate_rsi(self, series, window):
        delta = series.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd(self, series, fast, slow, signal):
        ema_fast = series.ewm(span=fast, min_periods=fast).mean()
        ema_slow = series.ewm(span=slow, min_periods=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, min_periods=signal).mean()
        return macd - macd_signal

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
