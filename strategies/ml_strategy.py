import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from .base_strategy import BaseStrategy
from .utils import generate_performance_chart
import ta
from loguru import logger

class MLStrategy(BaseStrategy):
    def __init__(self, config, params=None):
        super().__init__(config, params)
        # 初始化時不設置 max_depth，延遲到 backtest
        self.model = None

    def _load_sentiment_score(self, symbol, timeframe):
        # 情緒分數載入邏輯（與 technical_strategy.py 保持一致）
        return 0.0  # 未來可替換為實際情緒分數載入邏輯

    def backtest(self, symbol, data, timeframe='daily'):
        df = self.load_data(symbol, timeframe)
        if df is None:
            return self._default_results()

        try:
            # 計算技術指標作為特徵
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=self.params['rsi_window']).rsi()
            df['macd'] = ta.trend.MACD(df['close'], window_fast=self.params['macd_fast'], 
                                      window_slow=self.params['macd_slow'], 
                                      window_sign=self.params['macd_signal']).macd()
            df['macd_signal'] = ta.trend.MACD(df['close'], window_fast=self.params['macd_fast'], 
                                            window_slow=self.params['macd_slow'], 
                                            window_sign=self.params['macd_signal']).macd_signal()
            df['bollinger_hband'] = ta.volatility.BollingerBands(df['close']).bollinger_hband()
            df['bollinger_lband'] = ta.volatility.BollingerBands(df['close']).bollinger_lband()
            sentiment_score = self._load_sentiment_score(symbol, timeframe)

            # 準備特徵和目標
            features = ['rsi', 'macd', 'macd_signal', 'bollinger_hband', 'bollinger_lband']
            df['sentiment'] = sentiment_score
            features.append('sentiment')

            # 移除含 NaN 的行
            df = df.dropna(subset=features + ['close'])

            if len(df) < self.params['min_data_length']:
                logger.error(f"{symbol} {timeframe} 數據不足以訓練模型: 實際 {len(df)} 筆，需 {self.params['min_data_length']} 筆")
                return self._default_results()

            # 準備訓練數據（假設未來一天的價格變動作為目標）
            df['future_return'] = df['close'].pct_change().shift(-1)
            df['target'] = np.where(df['future_return'] > self.params['return_threshold'], 1, 
                                   np.where(df['future_return'] < -self.params['return_threshold'], -1, 0))
            
            # 分割訓練和測試數據（最後一筆用於預測）
            train_df = df.iloc[:-1]
            test_df = df.iloc[-1:]

            X_train = train_df[features]
            y_train = train_df['target']
            X_test = test_df[features]

            # 初始化模型，確保 max_depth 是單一值
            self.model = RandomForestClassifier(
                n_estimators=self.params.get('n_estimators', 100),
                max_depth=self.params.get('max_depth', None),  # 確保是單一值
                random_state=42
            )

            # 訓練模型
            self.model.fit(X_train, y_train)

            # 預測信號
            df['signal'] = 0
            df.iloc[-1, df.columns.get_loc('signal')] = self.model.predict(X_test)[0]

            # 計算回報
            df['returns'] = df['close'].pct_change()
            df['strategy_returns'] = df['returns'] * df['signal'].shift(1)
            sharpe_ratio = df['strategy_returns'].mean() / df['strategy_returns'].std() * np.sqrt(
                self.config['strategy_params']['sharpe_annualization_daily'] if timeframe == 'daily' else self.config['strategy_params']['sharpe_annualization_hourly']
            ) if df['strategy_returns'].std() != 0 else 0
            max_drawdown = (df['strategy_returns'].cumsum().cummax() - df['strategy_returns'].cumsum()).max()
            expected_return = df['strategy_returns'].mean() * (
                self.config['strategy_params']['expected_return_annualization_daily'] if timeframe == 'daily' else self.config['strategy_params']['expected_return_annualization_hourly']
            )

            # 生成信號
            latest_close = df['close'].iloc[-1]
            multiplier = self.config['strategy_params']['daily_multiplier'] if timeframe == 'daily' else self.config['strategy_params']['hourly_multiplier']
            signals = {
                'position': 'LONG' if df['signal'].iloc[-1] == 1 else 'NEUTRAL' if df['signal'].iloc[-1] == 0 else 'SHORT',
                'entry_price': latest_close,
                'target_price': latest_close * multiplier,
                'stop_loss': latest_close * self.config['strategy_params']['stop_loss_ratio'],
                'position_size': self.config['strategy_params']['position_size']
            }

            # 生成績效圖表
            generate_performance_chart(df, symbol, timeframe)

            return {
                'sharpe_ratio': sharpe_ratio if not np.isnan(sharpe_ratio) else 0,
                'max_drawdown': max_drawdown if not np.isnan(max_drawdown) else 0,
                'expected_return': expected_return if not np.isnan(expected_return) else 0,
                'signals': signals
            }
        except Exception as e:
            logger.error(f"{symbol} {timeframe} 回測失敗: {str(e)}")
            return self._default_results()
