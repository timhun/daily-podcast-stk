# strategy_mastermind.py
# strategy_mastermind.py
import pandas as pd
import numpy as np
from xai_sdk import Client
from xai_sdk.chat import user, system
import os
import json
from loguru import logger
import ta
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import itertools
from copy import deepcopy

# 載入 config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 配置日誌
logger.add(config['logging']['file'], rotation=config['logging']['rotation'])

class TechnicalAnalysis:
    def __init__(self):
        self.params = config.get('technical_params', {
            'rsi_window': 14,
            'rsi_buy_threshold': 30,
            'rsi_sell_threshold': 70,
            'sma_window': 20,
            'min_data_length_rsi_sma': 50
        })

    def backtest(self, symbol, data, timeframe='daily'):
        file_path = f"{config['data_paths']['market']}/{timeframe}_{symbol.replace('^', '').replace('.', '_')}.csv"
        if not os.path.exists(file_path):
            logger.error(f"{symbol} {timeframe} 歷史數據檔案不存在: {file_path}")
            return {
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'expected_return': 0,
                'signals': {}
            }
        
        try:
            df = pd.read_csv(file_path)
            if df.empty or len(df) < self.params['min_data_length_rsi_sma']:
                logger.error(f"{symbol} {timeframe} 數據不足: 實際 {len(df)} 筆，需 {self.params['min_data_length_rsi_sma']} 筆")
                return {
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'expected_return': 0,
                    'signals': {}
                }
            
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=self.params['rsi_window']).rsi()
            df['sma_20'] = ta.trend.SMAIndicator(df['close'], window=self.params['sma_window']).sma_indicator()
            
            df['bollinger_hband'] = ta.volatility.BollingerBands(df['close']).bollinger_hband()
            df['bollinger_lband'] = ta.volatility.BollingerBands(df['close']).bollinger_lband()
            sentiment_score = self._load_sentiment_score(symbol, timeframe)  # 新增方法
            df['signal'] = 0
            df.loc[(df['rsi'] < self.params['rsi_buy_threshold']) & 
                   (df['macd'] > df['macd_signal']) & 
                   (df['close'] <= df['bollinger_lband']) & 
                   (sentiment_score > 0.5), 'signal'] = 1
            df.loc[(df['rsi'] > self.params['rsi_sell_threshold']) & 
                   (df['macd'] < df['macd_signal']) & 
                   (df['close'] >= df['bollinger_hband']) & 
                   (sentiment_score < -0.5), 'signal'] = -1
            
            df['returns'] = df['close'].pct_change()
            df['strategy_returns'] = df['returns'] * df['signal'].shift(1)
            sharpe_ratio = df['strategy_returns'].mean() / df['strategy_returns'].std() * np.sqrt(
                config['strategy_params']['sharpe_annualization_daily'] if timeframe == 'daily' else config['strategy_params']['sharpe_annualization_hourly']
            ) if df['strategy_returns'].std() != 0 else 0
            max_drawdown = (df['strategy_returns'].cumsum().cummax() - df['strategy_returns'].cumsum()).max()
            expected_return = df['strategy_returns'].mean() * (
                config['strategy_params']['expected_return_annualization_daily'] if timeframe == 'daily' else config['strategy_params']['expected_return_annualization_hourly']
            )
            
            latest_close = df['close'].iloc[-1]
            multiplier = config['strategy_params']['daily_multiplier'] if timeframe == 'daily' else config['strategy_params']['hourly_multiplier']
            signals = {
                'position': 'LONG' if df['signal'].iloc[-1] == 1 else 'NEUTRAL' if df['signal'].iloc[-1] == 0 else 'SHORT',
                'entry_price': latest_close,
                'target_price': latest_close * multiplier,
                'stop_loss': latest_close * config['strategy_params']['stop_loss_ratio'],
                'position_size': config['strategy_params']['position_size']
            }
            
            self.generate_performance_chart(df, symbol, timeframe)
            
            return {
                'sharpe_ratio': sharpe_ratio if not np.isnan(sharpe_ratio) else 0,
                'max_drawdown': max_drawdown if not np.isnan(max_drawdown) else 0,
                'expected_return': expected_return if not np.isnan(expected_return) else 0,
                'signals': signals
            }
        except Exception as e:
            logger.error(f"{symbol} {timeframe} 回測失敗: {str(e)}")
            return {
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'expected_return': 0,
                'signals': {}
            }

    def generate_performance_chart(self, df, symbol, timeframe):
        df['cum_strategy_returns'] = (1 + df['strategy_returns']).cumprod() - 1
        df['cum_returns'] = (1 + df['returns']).cumprod() - 1
        
        plt.figure(figsize=(10, 6))
        plt.plot(df['date'], df['cum_strategy_returns'], label='Technical Strategy Returns')
        plt.plot(df['date'], df['cum_returns'], label='Buy & Hold Returns')
        plt.title(f'{symbol} {timeframe.upper()} Technical Strategy Performance')
        plt.xlabel('Date')
        plt.ylabel('Cumulative Returns')
        plt.legend()
        plt.grid(True)
        
        chart_dir = f"{config['data_paths']['charts']}/{datetime.today().strftime('%Y-%m-%d')}"
        os.makedirs(chart_dir, exist_ok=True)
        chart_path = f"{chart_dir}/{symbol.replace('^', '').replace('.', '_')}_{timeframe}_technical.png"
        plt.savefig(chart_path)
        plt.close()
        logger.info(f"技術分析策略表現圖表儲存至: {chart_path}")

class QuantityStrategy:
    def __init__(self):
        self.params = config.get('strategy_params', {}).get('quantity_params', {
            'volume_ma_period': 5,
            'volume_multiplier': 1.2,
            'stop_profit': 0.02,
            'stop_loss': 0.02,
            'risk_per_trade': 0.02
        })

    def backtest(self, symbol, data, timeframe='daily'):
        file_path = f"{config['data_paths']['market']}/{timeframe}_{symbol.replace('^', '').replace('.', '_')}.csv"
        if not os.path.exists(file_path):
            logger.error(f"{symbol} {timeframe} 歷史數據檔案不存在: {file_path}")
            return {
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'expected_return': 0,
                'signals': {}
            }

        try:
            df = pd.read_csv(file_path)
            if df.empty or len(df) < self.params['volume_ma_period']:
                logger.error(f"{symbol} {timeframe} 數據不足: {len(df)} 筆")
                return {
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'expected_return': 0,
                    'signals': {}
                }

            df['volume_ma'] = ta.trend.SMAIndicator(df['volume'], window=self.params['volume_ma_period']).sma_indicator()
            df['volume_rate'] = df['volume'] / df['volume_ma'].replace(0, np.nan)
            df['returns'] = df['close'].pct_change()

            df['signal'] = 0
            position = 0
            entry_price = 0
            trades = []
            win_count = 0
            total_trades = 0

            for i in range(1, len(df)):
                if df['volume_rate'].iloc[i] > self.params['volume_multiplier'] and df['close'].iloc[i] > df['close'].iloc[i-1] and position == 0:
                    df.loc[df.index[i], 'signal'] = 1
                    position = 1
                    entry_price = df['close'].iloc[i]
                elif position == 1:
                    if df['volume_rate'].iloc[i] < 1 and df['close'].iloc[i] < df['close'].iloc[i-1]:
                        df.loc[df.index[i], 'signal'] = -1
                        position = 0
                        trade_return = (df['close'].iloc[i] - entry_price) / entry_price
                        trades.append(trade_return)
                        total_trades += 1
                        if trade_return > 0:
                            win_count += 1
                    elif df['close'].iloc[i] >= entry_price * (1 + self.params['stop_profit']):
                        df.loc[df.index[i], 'signal'] = -1
                        position = 0
                        trade_return = self.params['stop_profit']
                        trades.append(trade_return)
                        total_trades += 1
                        win_count += 1
                    elif df['close'].iloc[i] <= entry_price * (1 - self.params['stop_loss']):
                        df.loc[df.index[i], 'signal'] = -1
                        position = 0
                        trade_return = -self.params['stop_loss']
                        trades.append(trade_return)
                        total_trades += 1

            df['strategy_returns'] = df['returns'] * df['signal'].shift(1)
            sharpe_ratio = df['strategy_returns'].mean() / df['strategy_returns'].std() * np.sqrt(
                config['strategy_params']['sharpe_annualization_daily'] if timeframe == 'daily' else config['strategy_params']['sharpe_annualization_hourly']
            ) if df['strategy_returns'].std() != 0 else 0
            max_drawdown = (df['strategy_returns'].cumsum().cummax() - df['strategy_returns'].cumsum()).max()
            expected_return = df['strategy_returns'].mean() * (
                config['strategy_params']['expected_return_annualization_daily'] if timeframe == 'daily' else config['strategy_params']['expected_return_annualization_hourly']
            )

            latest_close = df['close'].iloc[-1]
            multiplier = config['strategy_params']['daily_multiplier'] if timeframe == 'daily' else config['strategy_params']['hourly_multiplier']
            signals = {
                'position': 'LONG' if df['signal'].iloc[-1] == 1 else 'NEUTRAL' if df['signal'].iloc[-1] == 0 else 'SHORT',
                'entry_price': latest_close,
                'target_price': latest_close * multiplier,
                'stop_loss': latest_close * config['strategy_params']['stop_loss_ratio'],
                'position_size': self.params['risk_per_trade']
            }

            strategy_dir = f"{config['data_paths']['strategy']}/{datetime.today().strftime('%Y-%m-%d')}"
            os.makedirs(strategy_dir, exist_ok=True)
            result = {
                'sharpe_ratio': sharpe_ratio if not np.isnan(sharpe_ratio) else 0,
                'max_drawdown': max_drawdown if not np.isnan(max_drawdown) else 0,
                'expected_return': expected_return if not np.isnan(expected_return) else 0,
                'signals': signals,
                'win_rate': win_count / total_trades if total_trades > 0 else 0
            }
            with open(f"{strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json", 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"量價策略結果儲存至: {strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json")

            self.generate_performance_chart(df, symbol, timeframe)
            
            return result

        except Exception as e:
            logger.error(f"{symbol} {timeframe} 回測失敗: {str(e)}")
            return {
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'expected_return': 0,
                'signals': {}
            }

    def generate_performance_chart(self, df, symbol, timeframe):
        df['cum_strategy_returns'] = (1 + df['strategy_returns']).cumprod() - 1
        df['cum_returns'] = (1 + df['returns']).cumprod() - 1
        
        plt.figure(figsize=(10, 6))
        plt.plot(df['date'], df['cum_strategy_returns'], label='Quantity Strategy Returns')
        plt.plot(df['date'], df['cum_returns'], label='Buy & Hold Returns')
        plt.title(f'{symbol} {timeframe.upper()} Quantity Strategy Performance')
        plt.xlabel('Date')
        plt.ylabel('Cumulative Returns')
        plt.legend()
        plt.grid(True)
        
        chart_dir = f"{config['data_paths']['charts']}/{datetime.today().strftime('%Y-%m-%d')}"
        os.makedirs(chart_dir, exist_ok=True)
        chart_path = f"{chart_dir}/{symbol.replace('^', '').replace('.', '_')}_{timeframe}_quantity.png"
        plt.savefig(chart_path)
        plt.close()
        logger.info(f"量價策略表現圖表儲存至: {chart_path}")

class RandomForestStrategy:
    def __init__(self):
        self.params = config.get('ml_params', {
            'rf_estimators': 100,
            'rf_random_state': 42,
            'ml_test_size': 0.2,
            'ml_features': ['open', 'high', 'low', 'close', 'volume'],
            'min_data_length_ml': 100
        })
        self.model = RandomForestClassifier(
            n_estimators=self.params['rf_estimators'],
            random_state=self.params['rf_random_state']
        )

    def backtest(self, symbol, data, timeframe='daily'):
        file_path = f"{config['data_paths']['market']}/{timeframe}_{symbol.replace('^', '').replace('.', '_')}.csv"
        if not os.path.exists(file_path):
            logger.error(f"{symbol} {timeframe} 歷史數據檔案不存在: {file_path}")
            return {
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'expected_return': 0,
                'signals': {}
            }
        
        try:
            df = pd.read_csv(file_path)
            if df.empty or len(df) < self.params['min_data_length_ml']:
                logger.error(f"{symbol} {timeframe} 數據不足: {len(df)} 筆")
                return {
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'expected_return': 0,
                    'signals': {}
                }
            
            features = self.params['ml_features']
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=config['technical_params']['rsi_window']).rsi()
            df['sma_20'] = ta.trend.SMAIndicator(df['close'], window=config['technical_params']['sma_window']).sma_indicator()
            df['returns'] = df['close'].pct_change()
            df['target'] = np.where(df['returns'].shift(-1) > 0, 1, 0)
            
            X = df[features + ['rsi', 'sma_20']].dropna()
            y = df['target'].loc[X.index]
            if len(X) < self.params['min_data_length_ml']:
                logger.error(f"{symbol} {timeframe} 特徵數據不足: {len(X)} 筆")
                return {
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'expected_return': 0,
                    'signals': {}
                }
            
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=self.params['ml_test_size'], random_state=self.params['rf_random_state'])
            self.model.fit(X_train, y_train)
            predictions = self.model.predict(X_test)
            accuracy = accuracy_score(y_test, predictions)
            
            df['signal'] = 0
            df.loc[X.index[-len(predictions):], 'signal'] = predictions
            df['strategy_returns'] = df['returns'] * df['signal'].shift(1)
            sharpe_ratio = df['strategy_returns'].mean() / df['strategy_returns'].std() * np.sqrt(
                config['strategy_params']['sharpe_annualization_daily'] if timeframe == 'daily' else config['strategy_params']['sharpe_annualization_hourly']
            ) if df['strategy_returns'].std() != 0 else 0
            max_drawdown = (df['strategy_returns'].cumsum().cummax() - df['strategy_returns'].cumsum()).max()
            expected_return = df['strategy_returns'].mean() * (
                config['strategy_params']['expected_return_annualization_daily'] if timeframe == 'daily' else config['strategy_params']['expected_return_annualization_hourly']
            )
            
            latest_close = df['close'].iloc[-1]
            latest_features = df[features + ['rsi', 'sma_20']].iloc[-1:].dropna()
            latest_signal = self.model.predict(latest_features)[0] if not latest_features.empty else 0
            multiplier = config['strategy_params']['daily_multiplier'] if timeframe == 'daily' else config['strategy_params']['hourly_multiplier']
            signals = {
                'position': 'LONG' if latest_signal == 1 else 'NEUTRAL' if latest_signal == 0 else 'SHORT',
                'entry_price': latest_close,
                'target_price': latest_close * multiplier,
                'stop_loss': latest_close * config['strategy_params']['stop_loss_ratio'],
                'position_size': config['strategy_params']['position_size']
            }
            
            result = {
                'sharpe_ratio': sharpe_ratio if not np.isnan(sharpe_ratio) else 0,
                'max_drawdown': max_drawdown if not np.isnan(max_drawdown) else 0,
                'expected_return': expected_return if not np.isnan(expected_return) else 0,
                'signals': signals,
                'accuracy': accuracy
            }
            
            strategy_dir = f"{config['data_paths']['strategy']}/{datetime.today().strftime('%Y-%m-%d')}"
            os.makedirs(strategy_dir, exist_ok=True)
            with open(f"{strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json", 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"隨機森林策略結果儲存至: {strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json")
            
            return result
        except Exception as e:
            logger.error(f"{symbol} {timeframe} 回測失敗: {str(e)}")
            return {
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'expected_return': 0,
                'signals': {}
            }

class BigLineStrategy:
    def __init__(self):
        self.params = config.get('strategy_params', {}).get('bigline_params', {
            'weights': [0.4, 0.35, 0.25],
            'ma_short': 5,
            'ma_mid': 20,
            'ma_long': 60,
            'vol_window': 60
        })

    def backtest(self, symbol, data, timeframe='daily'):
        file_path = f"{config['data_paths']['market']}/{timeframe}_{symbol.replace('^', '').replace('.', '_')}.csv"
        index_symbol = '^TWII' if symbol in config['symbols']['tw'] else '^IXIC'
        index_file_path = f"{config['data_paths']['market']}/{timeframe}_{index_symbol.replace('^', '').replace('.', '_')}.csv"
        
        if not os.path.exists(file_path) or not os.path.exists(index_file_path):
            logger.error(f"{symbol} 或大盤 {index_symbol} {timeframe} 歷史數據檔案不存在")
            return {
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'expected_return': 0,
                'signals': {}
            }
        
        try:
            df = pd.read_csv(file_path)
            index_df = pd.read_csv(index_file_path)
            if df.empty or len(df) < self.params['ma_long'] or index_df.empty or len(index_df) < self.params['ma_long']:
                logger.error(f"{symbol} 或大盤 {index_symbol} {timeframe} 數據不足")
                return {
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'expected_return': 0,
                    'signals': {}
                }
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').set_index('date')
            index_df['date'] = pd.to_datetime(index_df['date'])
            index_df = index_df.sort_values('date').set_index('date')
            
            df = df.join(index_df[['close', 'volume']], rsuffix='_index', how='inner')
            
            prices = df['close']
            volume = df['volume']
            index_prices = df['close_index']
            
            ma_short = prices.rolling(window=self.params['ma_short']).mean()
            ma_mid = prices.rolling(window=self.params['ma_mid']).mean()
            ma_long = prices.rolling(window=self.params['ma_long']).mean()
            bullish = (ma_short > ma_mid) & (ma_mid > ma_long)
            
            big_line = (self.params['weights'][0] * ma_short +
                        self.params['weights'][1] * ma_mid +
                        self.params['weights'][2] * ma_long)
            
            max_vol = volume.rolling(window=self.params['vol_window']).max()
            vol_factor = 1 + volume / (max_vol + 1e-9)
            big_line_weighted = big_line * vol_factor
            big_line_diff = big_line_weighted.diff()
            
            index_ma_short = index_prices.rolling(window=self.params['ma_short']).mean()
            index_ma_mid = index_prices.rolling(window=self.params['ma_mid']).mean()
            index_ma_long = index_prices.rolling(window=self.params['ma_long']).mean()
            index_bullish = (index_ma_short > index_ma_mid) & (index_ma_mid > index_ma_long)
            
            df['signal'] = 0
            df.loc[(big_line_diff > 0) & bullish & index_bullish, 'signal'] = 1
            df.loc[(big_line_diff < 0) & ~index_bullish, 'signal'] = -1
            
            df['returns'] = df['close'].pct_change()
            df['strategy_returns'] = df['returns'] * df['signal'].shift(1)
            
            sharpe_ratio = df['strategy_returns'].mean() / df['strategy_returns'].std() * np.sqrt(
                config['strategy_params']['sharpe_annualization_daily'] if timeframe == 'daily' else config['strategy_params']['sharpe_annualization_hourly']
            ) if df['strategy_returns'].std() != 0 else 0
            sharpe_ratio = sharpe_ratio if not np.isnan(sharpe_ratio) else 0
            
            cum_returns = df['strategy_returns'].cumsum()
            max_drawdown = (cum_returns.cummax() - cum_returns).max()
            max_drawdown = max_drawdown if not np.isnan(max_drawdown) else 0
            
            expected_return = df['strategy_returns'].mean() * (
                config['strategy_params']['expected_return_annualization_daily'] if timeframe == 'daily' else config['strategy_params']['expected_return_annualization_hourly']
            )
            expected_return = expected_return if not np.isnan(expected_return) else 0
            
            latest_close = df['close'].iloc[-1]
            multiplier = config['strategy_params']['daily_multiplier'] if timeframe == 'daily' else config['strategy_params']['hourly_multiplier']
            signals = {
                'position': 'LONG' if df['signal'].iloc[-1] == 1 else 'SHORT' if df['signal'].iloc[-1] == -1 else 'NEUTRAL',
                'entry_price': latest_close,
                'target_price': latest_close * multiplier,
                'stop_loss': latest_close * config['strategy_params']['stop_loss_ratio'],
                'position_size': config['strategy_params']['position_size']
            }
            
            self.generate_performance_chart(df, symbol, timeframe)
            
            return {
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'expected_return': expected_return,
                'signals': signals
            }
        except Exception as e:
            logger.error(f"{symbol} {timeframe} 回測失敗: {str(e)}")
            return {
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'expected_return': 0,
                'signals': {}
            }

    def generate_performance_chart(self, df, symbol, timeframe):
        df['cum_strategy_returns'] = (1 + df['strategy_returns']).cumprod() - 1
        df['cum_returns'] = (1 + df['returns']).cumprod() - 1
        
        plt.figure(figsize=(10, 6))
        plt.plot(df.index, df['cum_strategy_returns'], label='BigLine Strategy Returns')
        plt.plot(df.index, df['cum_returns'], label='Buy & Hold Returns')
        plt.title(f'{symbol} {timeframe.upper()} BigLine Strategy Performance')
        plt.xlabel('Date')
        plt.ylabel('Cumulative Returns')
        plt.legend()
        plt.grid(True)
        
        chart_dir = f"{config['data_paths']['charts']}/{datetime.today().strftime('%Y-%m-%d')}"
        os.makedirs(chart_dir, exist_ok=True)
        chart_path = f"{chart_dir}/{symbol.replace('^', '').replace('.', '_')}_{timeframe}_bigline.png"
        plt.savefig(chart_path)
        plt.close()
        logger.info(f"BigLine 策略表現圖表儲存至: {chart_path}")

class MarketAnalyst:
    def __init__(self):
        pass

    def analyze_market(self, symbol, timeframe='daily'):
        file_path = f"{config['data_paths']['market']}/{timeframe}_{symbol.replace('^', '').replace('.', '_')}.csv"
        if not os.path.exists(file_path):
            logger.error(f"{symbol} {timeframe} 數據檔案不存在: {file_path}")
            return {
                'trend': 'NEUTRAL',
                'volatility': 0.0,
                'technical_indicators': {},
                'report': '無數據可分析'
            }
        
        try:
            df = pd.read_csv(file_path)
            if df.empty or len(df) < 50:
                logger.error(f"{symbol} {timeframe} 數據不足: {len(df)} 筆")
                return {
                    'trend': 'NEUTRAL',
                    'volatility': 0.0,
                    'technical_indicators': {},
                    'report': '數據不足'
                }
            
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            df['macd'] = ta.trend.MACD(df['close']).macd()
            df['bollinger_hband'] = ta.volatility.BollingerBands(df['close']).bollinger_hband()
            df['bollinger_lband'] = ta.volatility.BollingerBands(df['close']).bollinger_lband()
            df['sma_50'] = ta.trend.SMAIndicator(df['close'], window=50).sma_indicator()
            df['sma_200'] = ta.trend.SMAIndicator(df['close'], window=200).sma_indicator()
            
            trend = 'NEUTRAL'
            if df['sma_50'].iloc[-1] > df['sma_200'].iloc[-1]:
                trend = 'BULLISH'
            elif df['sma_50'].iloc[-1] < df['sma_200'].iloc[-1]:
                trend = 'BEARISH'
            
            volatility = df['close'].pct_change().rolling(20).std().iloc[-1] * 100 if 'close' in df else 0.0
            
            indicators = {
                'rsi': df['rsi'].iloc[-1],
                'macd': df['macd'].iloc[-1],
                'bollinger': {
                    'high': df['bollinger_hband'].iloc[-1],
                    'low': df['bollinger_lband'].iloc[-1]
                }
            }
            
            report = f"{symbol} 市場分析：趨勢 {trend}，波動性 {volatility:.2f}%，RSI {indicators['rsi']:.2f}，MACD {indicators['macd']:.2f}。"
            
            logger.info(f"{symbol} 市場分析完成")
            return {
                'trend': trend,
                'volatility': volatility,
                'technical_indicators': indicators,
                'report': report
            }
        except Exception as e:
            logger.error(f"{symbol} 市場分析失敗: {str(e)}")
            return {
                'trend': 'NEUTRAL',
                'volatility': 0.0,
                'technical_indicators': {},
                'report': '分析失敗'
            }

class StrategyEngine:
    def __init__(self):
        self.models = {
            'technical': TechnicalAnalysis(),
            'random_forest': RandomForestStrategy(),
            'quantity': QuantityStrategy(),
            'bigline': BigLineStrategy()
        }
        self.api_key = os.getenv("GROK_API_KEY")
        if not self.api_key:
            logger.error("GROK_API_KEY 未設置")
            raise EnvironmentError("GROK_API_KEY 未設置")
        
        # 定義參數搜索範圍
        self.param_grid = {
            'technical': {
                'rsi_window': [10, 14, 20],
                'rsi_buy_threshold': [25, 30, 35],
                'rsi_sell_threshold': [65, 70, 75]
            },
            'random_forest': {
                'rf_estimators': [50, 100, 200]
            },
            'quantity': {
                'volume_ma_period': [3, 5, 7],
                'volume_multiplier': [1.1, 1.2, 1.3]
            },
            'bigline': {
                'weights': [[0.4, 0.35, 0.25], [0.5, 0.3, 0.2], [0.3, 0.4, 0.3]],
                'ma_short': [3, 5, 7]
            }
        }

    def run_strategy_tournament(self, symbol, data, timeframe='daily'):
        results = {}
        best_results = {}
        
        for name, strategy in self.models.items():
            best_score = -float('inf')
            best_params = None
            best_result = None
            
            # 網格搜索參數
            param_combinations = self._get_param_combinations(name)
            for params in param_combinations:
                # 臨時修改策略參數
                original_params = deepcopy(getattr(strategy, 'params', {}))
                strategy.params = params
                
                try:
                    result = strategy.backtest(symbol, data, timeframe)
                    score = result['sharpe_ratio'] if result['max_drawdown'] < config['strategy_params']['max_drawdown_threshold'] else -float('inf')
                    
                    if score > best_score:
                        best_score = score
                        best_params = params
                        best_result = result
                        
                    logger.info(f"{symbol} {name} 策略參數 {params} 回測完成，Sharpe: {result['sharpe_ratio']:.2f}")
                except Exception as e:
                    logger.error(f"{symbol} {name} 參數 {params} 回測失敗: {str(e)}")
                
                # 恢復原始參數
                strategy.params = original_params
            
            results[name] = best_result or {
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'expected_return': 0,
                'signals': {}
            }
            best_results[name] = {
                'params': best_params,
                'result': best_result
            }
        
        # 使用 Grok API 選擇最佳策略
        optimized = self.optimize_with_grok(symbol, results, timeframe)
        if optimized is None:
            logger.error(f"{symbol} 優化結果為 None，返回預設結果")
            optimized = {
                'symbol': symbol,
                'analysis_date': datetime.today().strftime('%Y-%m-%d'),
                'index_symbol': '^TWII' if symbol in config['symbols']['tw'] else '^IXIC',
                'winning_strategy': {
                    'name': 'none',
                    'confidence': 0.0,
                    'expected_return': 0.0,
                    'max_drawdown': 0.0,
                    'sharpe_ratio': 0.0
                },
                'signals': {
                    'position': 'NEUTRAL',
                    'entry_price': 0.0,
                    'target_price': 0.0,
                    'stop_loss': 0.0,
                    'position_size': 0.0
                }
            }
        
        # 儲存最佳策略結果
        strategy_dir = f"{config['data_paths']['strategy']}/{datetime.today().strftime('%Y-%m-%d')}"
        os.makedirs(strategy_dir, exist_ok=True)
        with open(f"{strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json", 'w', encoding='utf-8') as f:
            json.dump(optimized, f, ensure_ascii=False, indent=2)
        logger.info(f"策略結果儲存至: {strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json")
        
        return optimized

    def _get_param_combinations(self, strategy_name):
        """生成參數組合"""
        params = self.param_grid.get(strategy_name, {})
        keys = list(params.keys())
        values = list(params.values())
        combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
        return combinations if combinations else [{}]

    def optimize_with_grok(self, symbol, results, timeframe):
        client = Client(api_key=self.api_key, timeout=3600)
        chat = client.chat.create(model="grok-3-mini")
        chat.append(system("You are an AI-driven financial strategy optimizer. Analyze strategy backtest results and select the best strategy based on Sharpe ratio, ensuring max drawdown < 15%."))

        index_symbol = '^TWII' if symbol in config['symbols']['tw'] else '^IXIC'
        prompt = (
            f"為股票 {symbol} 選擇最佳策略（時間框架: {timeframe}，大盤參考: {index_symbol}）。以下是回測結果：\n"
            f"{json.dumps(results, ensure_ascii=False, indent=2)}\n"
            "要求：\n"
            f"- 選擇夏普比率最高的策略，且最大回撤 < {config['strategy_params']['max_drawdown_threshold']}。\n"
            "- 提供最佳策略名稱、信心分數、預期回報、最大回撤、夏普比率和交易信號。\n"
            "- 格式為 JSON:\n"
            "```json\n"
            "{\n"
            f'  "symbol": "{symbol}",\n'
            f'  "analysis_date": "{datetime.today().strftime("%Y-%m-%d")}",\n'
            f'  "index_symbol": "{index_symbol}",\n'
            '  "winning_strategy": {\n'
            '    "name": "strategy_name",\n'
            '    "confidence": 0.0,\n'
            '    "expected_return": 0.0,\n'
            '    "max_drawdown": 0.0,\n'
            '    "sharpe_ratio": 0.0\n'
            '  },\n'
            '  "signals": {\n'
            '    "position": "LONG/NEUTRAL/SHORT",\n'
            '    "entry_price": 0.0,\n'
            '    "target_price": 0.0,\n'
            '    "stop_loss": 0.0,\n'
            '    "position_size": 0.0\n'
            '  }\n'
            '}\n'
            '```'
        )
        chat.append(user(prompt))
        response = chat.sample()
        
        try:
            optimized = json.loads(response.content.strip('```json\n').strip('\n```'))
            return optimized
        except json.JSONDecodeError:
            logger.error("Grok 回應 JSON 解析失敗")
            return None
