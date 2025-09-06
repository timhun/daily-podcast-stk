#strategy_mastermind.py
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

# 載入 config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 配置日誌
logger.add(config['logging']['file'], rotation=config['logging']['rotation'])

class TechnicalAnalysis:
    def __init__(self):
        pass

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
            if df.empty or len(df) < config['technical_params']['min_data_length_rsi_sma']:
                logger.error(f"{symbol} {timeframe} 數據不足: {len(df)} 筆")
                return {
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'expected_return': 0,
                    'signals': {}
                }
            
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=config['technical_params']['rsi_window']).rsi()
            df['sma_20'] = ta.trend.SMAIndicator(df['close'], window=config['technical_params']['sma_window']).sma_indicator()
            
            df['signal'] = 0
            df.loc[df['rsi'] < config['technical_params']['rsi_buy_threshold'], 'signal'] = 1
            df.loc[df['rsi'] > config['technical_params']['rsi_sell_threshold'], 'signal'] = -1
            
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
        plt.plot(df['date'], df['cum_strategy_returns'], label='Strategy Returns')
        plt.plot(df['date'], df['cum_returns'], label='Buy & Hold Returns')
        plt.title(f'{symbol} {timeframe.upper()} Performance')
        plt.xlabel('Date')
        plt.ylabel('Cumulative Returns')
        plt.legend()
        plt.grid(True)
        
        chart_dir = f"{config['data_paths']['charts']}/{datetime.today().strftime('%Y-%m-%d')}"
        os.makedirs(chart_dir, exist_ok=True)
        chart_path = f"{chart_dir}/{symbol.replace('^', '').replace('.', '_')}_{timeframe}.png"
        plt.savefig(chart_path)
        plt.close()
        logger.info(f"策略表現圖表儲存至: {chart_path}")

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

            # 計算成交量均線
            df['volume_ma'] = ta.trend.SMAIndicator(df['volume'], window=self.params['volume_ma_period']).sma_indicator()
            df['volume_rate'] = df['volume'] / df['volume_ma'].replace(0, np.nan)
            df['returns'] = df['close'].pct_change()

            # 初始化信號和持倉
            df['signal'] = 0
            position = 0
            entry_price = 0
            trades = []
            win_count = 0
            total_trades = 0

            # 模擬交易邏輯
            for i in range(1, len(df)):
                if df['volume_rate'].iloc[i] > self.params['volume_multiplier'] and df['close'].iloc[i] > df['close'].iloc[i-1] and position == 0:
                    df.loc[df.index[i], 'signal'] = 1  # 買入
                    position = 1
                    entry_price = df['close'].iloc[i]
                elif position == 1:
                    if df['volume_rate'].iloc[i] < 1 and df['close'].iloc[i] < df['close'].iloc[i-1]:
                        df.loc[df.index[i], 'signal'] = -1  # 賣出 (量縮價跌)
                        position = 0
                        trade_return = (df['close'].iloc[i] - entry_price) / entry_price
                        trades.append(trade_return)
                        total_trades += 1
                        if trade_return > 0:
                            win_count += 1
                    elif df['close'].iloc[i] >= entry_price * (1 + self.params['stop_profit']):
                        df.loc[df.index[i], 'signal'] = -1  # 賣出 (停利)
                        position = 0
                        trade_return = self.params['stop_profit']
                        trades.append(trade_return)
                        total_trades += 1
                        win_count += 1
                    elif df['close'].iloc[i] <= entry_price * (1 - self.params['stop_loss']):
                        df.loc[df.index[i], 'signal'] = -1  # 賣出 (停損)
                        position = 0
                        trade_return = -self.params['stop_loss']
                        trades.append(trade_return)
                        total_trades += 1

            # 計算策略回報
            df['strategy_returns'] = df['returns'] * df['signal'].shift(1)
            sharpe_ratio = df['strategy_returns'].mean() / df['strategy_returns'].std() * np.sqrt(
                config['strategy_params']['sharpe_annualization_daily'] if timeframe == 'daily' else config['strategy_params']['sharpe_annualization_hourly']
            ) if df['strategy_returns'].std() != 0 else 0
            max_drawdown = (df['strategy_returns'].cumsum().cummax() - df['strategy_returns'].cumsum()).max()
            expected_return = df['strategy_returns'].mean() * (
                config['strategy_params']['expected_return_annualization_daily'] if timeframe == 'daily' else config['strategy_params']['expected_return_annualization_hourly']
            )

            # 最新交易信號
            latest_close = df['close'].iloc[-1]
            multiplier = config['strategy_params']['daily_multiplier'] if timeframe == 'daily' else config['strategy_params']['hourly_multiplier']
            signals = {
                'position': 'LONG' if df['signal'].iloc[-1] == 1 else 'NEUTRAL' if df['signal'].iloc[-1] == 0 else 'SHORT',
                'entry_price': latest_close,
                'target_price': latest_close * multiplier,
                'stop_loss': latest_close * config['strategy_params']['stop_loss_ratio'],
                'position_size': self.params['risk_per_trade']
            }

            # 儲存策略結果
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
            logger.info(f"策略結果儲存至: {strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json")

            # 生成表現圖表
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
        plt.plot(df['date'], df['cum_strategy_returns'], label='Strategy Returns')
        plt.plot(df['date'], df['cum_returns'], label='Buy & Hold Returns')
        plt.title(f'{symbol} {timeframe.upper()} Performance')
        plt.xlabel('Date')
        plt.ylabel('Cumulative Returns')
        plt.legend()
        plt.grid(True)
        
        chart_dir = f"{config['data_paths']['charts']}/{datetime.today().strftime('%Y-%m-%d')}"
        os.makedirs(chart_dir, exist_ok=True)
        chart_path = f"{chart_dir}/{symbol.replace('^', '').replace('.', '_')}_{timeframe}.png"
        plt.savefig(chart_path)
        plt.close()
        logger.info(f"策略表現圖表儲存至: {chart_path}")

class RandomForestStrategy:
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=config['ml_params']['rf_estimators'],
            random_state=config['ml_params']['rf_random_state']
        )
        self.api_key = os.getenv('GROK_API_KEY')

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
            if df.empty or len(df) < config['technical_params']['min_data_length_ml']:
                logger.error(f"{symbol} {timeframe} 數據不足: {len(df)} 筆")
                return {
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'expected_return': 0,
                    'signals': {}
                }
            
            features = config['ml_params']['ml_features']
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=config['technical_params']['rsi_window']).rsi()
            df['sma_20'] = ta.trend.SMAIndicator(df['close'], window=config['technical_params']['sma_window']).sma_indicator()
            df['returns'] = df['close'].pct_change()
            df['target'] = np.where(df['returns'].shift(-1) > 0, 1, 0)
            
            X = df[features + ['rsi', 'sma_20']].dropna()
            y = df['target'].loc[X.index]
            if len(X) < config['technical_params']['min_data_length_ml']:
                logger.error(f"{symbol} {timeframe} 特徵數據不足: {len(X)} 筆")
                return {
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'expected_return': 0,
                    'signals': {}
                }
            
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=config['ml_params']['ml_test_size'], random_state=config['ml_params']['rf_random_state'])
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
            logger.info(f"策略結果儲存至: {strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json")
            
            return result
        except Exception as e:
            logger.error(f"{symbol} {timeframe} 回測失敗: {str(e)}")
            return {
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'expected_return': 0,
                'signals': {}
            }

    def optimize_with_grok(self, symbol, results, timeframe):
        client = Client(api_key=self.api_key, timeout=3600)
        chat = client.chat.create(model="grok-3-mini")
        chat.append(system("You are an AI-driven financial strategy optimizer. Analyze strategy backtest results and select the best strategy based on Sharpe ratio, ensuring max drawdown < 15%."))

        prompt = (
            f"為股票 {symbol} 選擇最佳策略（時間框架: {timeframe}）。以下是回測結果：\n"
            f"{json.dumps(results, ensure_ascii=False, indent=2)}\n"
            "要求：\n"
            f"- 選擇夏普比率最高的策略，且最大回撤 < {config['strategy_params']['max_drawdown_threshold']}。\n"
            "- 提供最佳策略名稱、信心分數、預期回報、最大回撤、夏普比率和交易信號。\n"
            "- 格式為 JSON:\n"
            "```json\n"
            "{\n"
            f'  "symbol": "{symbol}",\n'
            f'  "analysis_date": "{datetime.today().strftime("%Y-%m-%d")}",\n'
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
            'quantity': QuantityStrategy()  # 新增 QuantityStrategy
        }
        self.api_key = os.getenv("GROK_API_KEY")
        if not self.api_key:
            logger.error("GROK_API_KEY 未設置")
            raise EnvironmentError("GROK_API_KEY 未設置")

    def run_strategy_tournament(self, symbol, data, timeframe='daily'):
        results = {}
        for name, strategy in self.models.items():
            try:
                results[name] = strategy.backtest(symbol, data, timeframe)
                logger.info(f"{symbol} {name} 策略回測完成 (timeframe: {timeframe})")
            except Exception as e:
                logger.error(f"{symbol} {name} 回測失敗: {str(e)}")
                results[name] = {
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'expected_return': 0,
                    'signals': {}
                }

        # 使用 Grok API 優化策略組合
        optimized = self.optimize_with_grok(symbol, results, timeframe)
        if optimized is None:
            logger.error(f"{symbol} 優化結果為 None，返回預設結果")
            optimized = {
                'symbol': symbol,
                'analysis_date': datetime.today().strftime('%Y-%m-%d'),
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
        # 儲存策略結果
        strategy_dir = f"{config['data_paths']['strategy']}/{datetime.today().strftime('%Y-%m-%d')}"
        os.makedirs(strategy_dir, exist_ok=True)
        with open(f"{strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json", 'w', encoding='utf-8') as f:
            json.dump(optimized, f, ensure_ascii=False, indent=2)
        logger.info(f"策略結果儲存至: {strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json")
        return optimized

    def optimize_with_grok(self, symbol, results, timeframe):
        client = Client(api_key=self.api_key, timeout=3600)
        chat = client.chat.create(model="grok-3-mini")
        chat.append(system("You are an AI-driven financial strategy optimizer. Analyze strategy backtest results and select the best strategy based on Sharpe ratio, ensuring max drawdown < 15%."))

        prompt = (
            f"為股票 {symbol} 選擇最佳策略（時間框架: {timeframe}）。以下是回測結果：\n"
            f"{json.dumps(results, ensure_ascii=False, indent=2)}\n"
            "要求：\n"
            f"- 選擇夏普比率最高的策略，且最大回撤 < {config['strategy_params']['max_drawdown_threshold']}。\n"
            "- 提供最佳策略名稱、信心分數、預期回報、最大回撤、夏普比率和交易信號。\n"
            "- 格式為 JSON:\n"
            "```json\n"
            "{\n"
            f'  "symbol": "{symbol}",\n'
            f'  "analysis_date": "{datetime.today().strftime("%Y-%m-%d")}",\n'
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
