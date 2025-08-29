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

    def backtest(self, symbol, data, timeframe='daily'):  # 修改 timeframe 為 'daily'
        # 修正檔案路徑
        file_path = f"data/market/{timeframe}_{symbol.replace('^', '').replace('.', '_')}.csv"
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
            if df.empty or len(df) < 20:  # 確保有足夠數據計算 RSI 和 SMA
                logger.error(f"{symbol} {timeframe} 數據不足: {len(df)} 筆")
                return {
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'expected_return': 0,
                    'signals': {}
                }
            
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            df['sma_20'] = ta.trend.SMAIndicator(df['close'], window=20).sma_indicator()
            
            # 簡單策略：RSI < 30 買入，RSI > 70 賣出
            df['signal'] = 0
            df.loc[df['rsi'] < 30, 'signal'] = 1  # 買入
            df.loc[df['rsi'] > 70, 'signal'] = -1  # 賣出
            
            # 計算回報和風險指標
            df['returns'] = df['close'].pct_change()
            df['strategy_returns'] = df['returns'] * df['signal'].shift(1)
            sharpe_ratio = df['strategy_returns'].mean() / df['strategy_returns'].std() * np.sqrt(252) if timeframe == 'daily' else np.sqrt(252 * 24)
            max_drawdown = (df['strategy_returns'].cumsum().cummax() - df['strategy_returns'].cumsum()).max()
            expected_return = df['strategy_returns'].mean() * (252 if timeframe == 'daily' else 252 * 24)
            
            # 最新交易信號
            latest_close = df['close'].iloc[-1]
            multiplier = 1.05 if timeframe == 'daily' else 1.02
            signals = {
                'position': 'LONG' if df['signal'].iloc[-1] == 1 else 'NEUTRAL' if df['signal'].iloc[-1] == 0 else 'SHORT',
                'entry_price': latest_close,
                'target_price': latest_close * multiplier,
                'stop_loss': latest_close * 0.95,
                'position_size': 0.5
            }
            
            # 生成策略表現圖表
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
        # 繪製累積回報圖
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
        
        chart_dir = f"data/charts/{datetime.today().strftime('%Y-%m-%d')}"
        os.makedirs(chart_dir, exist_ok=True)
        chart_path = f"{chart_dir}/{symbol.replace('^', '').replace('.', '_')}_{timeframe}.png"
        plt.savefig(chart_path)
        plt.close()
        logger.info(f"策略表現圖表儲存至: {chart_path}")

class RandomForestStrategy:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)

    def backtest(self, symbol, data, timeframe='daily'):  # 修改 timeframe 為 'daily'
        # 修正檔案路徑
        file_path = f"data/market/{timeframe}_{symbol.replace('^', '').replace('.', '_')}.csv"
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
            if df.empty or len(df) < 50:  # 需要更多數據來訓練模型
                logger.error(f"{symbol} {timeframe} 數據不足: {len(df)} 筆")
                return {
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'expected_return': 0,
                    'signals': {}
                }
            
            # 特徵工程
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            df['sma_20'] = ta.trend.SMAIndicator(df['close'], window=20).sma_indicator()
            df['sma_50'] = ta.trend.SMAIndicator(df['close'], window=50).sma_indicator()
            df['momentum'] = df['close'].pct_change(5)
            df.dropna(inplace=True)
            
            # 目標變量：未來1期的方向 (1: 上漲, 0: 下跌)
            df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
            
            # 訓練/測試分割
            features = ['rsi', 'sma_20', 'sma_50', 'momentum']
            X = df[features]
            y = df['target']
            X_train, X_test, y_train, y_test = train_test_split(X[:-1], y[:-1], test_size=0.2, shuffle=False)
            
            # 訓練模型
            self.model.fit(X_train, y_train)
            
            # 預測
            df['signal'] = 0
            test_index = df.index[-len(X_test):]
            predictions = self.model.predict(X_test)
            df.loc[test_index, 'signal'] = np.where(predictions == 1, 1, -1)  # 1: LONG, -1: SHORT
            
            # 計算準確率
            accuracy = accuracy_score(y_test, predictions)
            logger.info(f"{symbol} RandomForest 準確率: {accuracy:.2f}")
            
            # 計算回報和風險指標
            df['returns'] = df['close'].pct_change()
            df['strategy_returns'] = df['returns'] * df['signal'].shift(1)
            sharpe_ratio = df['strategy_returns'].mean() / df['strategy_returns'].std() * np.sqrt(252) if timeframe == 'daily' else np.sqrt(252 * 24)
            max_drawdown = (df['strategy_returns'].cumsum().cummax() - df['strategy_returns'].cumsum()).max()
            expected_return = df['strategy_returns'].mean() * (252 if timeframe == 'daily' else 252 * 24)
            
            # 最新交易信號
            latest_close = df['close'].iloc[-1]
            latest_features = df[features].iloc[-1:].values
            latest_pred = self.model.predict(latest_features)[0]
            position = 'LONG' if latest_pred == 1 else 'SHORT'
            multiplier = 1.05 if timeframe == 'daily' else 1.02
            signals = {
                'position': position,
                'entry_price': latest_close,
                'target_price': latest_close * multiplier if latest_pred == 1 else latest_close * 0.95,
                'stop_loss': latest_close * 0.95 if latest_pred == 1 else latest_close * 1.05,
                'position_size': 0.5
            }
            
            # 生成策略表現圖表
            self.generate_performance_chart(df, symbol, timeframe)
            
            return {
                'sharpe_ratio': sharpe_ratio if not np.isnan(sharpe_ratio) else 0,
                'max_drawdown': max_drawdown if not np.isnan(max_drawdown) else 0,
                'expected_return': expected_return if not np.isnan(expected_return) else 0,
                'signals': signals
            }
        except Exception as e:
            logger.error(f"{symbol} {timeframe} RandomForest 回測失敗: {str(e)}")
            return {
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'expected_return': 0,
                'signals': {}
            }

    def generate_performance_chart(self, df, symbol, timeframe):
        # 繪製累積回報圖
        df['cum_strategy_returns'] = (1 + df['strategy_returns']).cumprod() - 1
        df['cum_returns'] = (1 + df['returns']).cumprod() - 1
        
        plt.figure(figsize=(10, 6))
        plt.plot(df['date'], df['cum_strategy_returns'], label='RandomForest Strategy Returns')
        plt.plot(df['date'], df['cum_returns'], label='Buy & Hold Returns')
        plt.title(f'{symbol} {timeframe.upper()} RandomForest Performance')
        plt.xlabel('Date')
        plt.ylabel('Cumulative Returns')
        plt.legend()
        plt.grid(True)
        
        chart_dir = f"data/charts/{datetime.today().strftime('%Y-%m-%d')}"
        os.makedirs(chart_dir, exist_ok=True)
        chart_path = f"{chart_dir}/{symbol.replace('^', '').replace('.', '_')}_{timeframe}_rf.png"
        plt.savefig(chart_path)
        plt.close()
        logger.info(f"RandomForest 策略表現圖表儲存至: {chart_path}")

class StrategyEngine:
    def __init__(self):
        self.models = {
            'technical': TechnicalAnalysis(),
            'random_forest': RandomForestStrategy(),
        }
        self.api_key = os.getenv("GROK_API_KEY")
        if not self.api_key:
            logger.error("GROK_API_KEY 未設置")
            raise EnvironmentError("GROK_API_KEY 未設置")

    def run_strategy_tournament(self, symbol, data, timeframe='daily'):  # 修改 timeframe 為 'daily'
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
        strategy_dir = f"data/strategy/{datetime.today().strftime('%Y-%m-%d')}"
        os.makedirs(strategy_dir, exist_ok=True)
        with open(f"{strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json", 'w', encoding='utf-8') as f:
            json.dump(optimized, f, ensure_ascii=False, indent=2)
        logger.info(f"策略結果儲存至: {strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json")
        return optimized

    def optimize_with_grok(self, symbol, results, timeframe):
        client = Client(api_key=self.api_key, timeout=3600)
        chat = client.chat.create(model="grok-3-mini")
        chat.append(system("You are an AI-driven financial strategy optimizer. Analyze strategy backtest results and select the best strategy based on Sharpe ratio, ensuring max drawdown < 15%."))

        # 使用三引號字符串並以 markdown 程式碼塊包裝 JSON，避免引號衝突
        prompt = (
            f"為股票 {symbol} 選擇最佳策略（時間框架: {timeframe}）。以下是回測結果：\n"
            f"{json.dumps(results, ensure_ascii=False, indent=2)}\n"
            "要求：\n"
            "- 選擇夏普比率最高的策略，且最大回撤 < 15%。\n"
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
            # 解析 Grok 的 JSON 回應
            optimized = json.loads(response.content.strip('```json\n').strip('\n```'))
            return optimized
        except json.JSONDecodeError:
            logger.error("Grok 回應 JSON 解析失敗")
            return None

class MarketAnalyst:
    def __init__(self):
        pass

    def analyze_market(self, symbol, timeframe='daily'):
        file_path = f"data/market/{timeframe}_{symbol.replace('^', '').replace('.', '_')}.csv"
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
            
            # 技術指標計算
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            df['macd'] = ta.trend.MACD(df['close']).macd()
            df['bollinger_hband'] = ta.volatility.BollingerBands(df['close']).bollinger_hband()
            df['bollinger_lband'] = ta.volatility.BollingerBands(df['close']).bollinger_lband()
            df['sma_50'] = ta.trend.SMAIndicator(df['close'], window=50).sma_indicator()
            df['sma_200'] = ta.trend.SMAIndicator(df['close'], window=200).sma_indicator()
            
            # 趨勢分析：黃金交叉/死亡交叉
            trend = 'NEUTRAL'
            if df['sma_50'].iloc[-1] > df['sma_200'].iloc[-1]:
                trend = 'BULLISH'  # 看漲
            elif df['sma_50'].iloc[-1] < df['sma_200'].iloc[-1]:
                trend = 'BEARISH'  # 看跌
            
            # 波動性：最近 20 期的標準差
            volatility = df['close'].pct_change().rolling(20).std().iloc[-1] * 100 if 'close' in df else 0.0
            
            # 指標摘要
            indicators = {
                'rsi': df['rsi'].iloc[-1],
                'macd': df['macd'].iloc[-1],
                'bollinger': {
                    'high': df['bollinger_hband'].iloc[-1],
                    'low': df['bollinger_lband'].iloc[-1]
                }
            }
            
            # 生成報告
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
