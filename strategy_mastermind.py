import pandas as pd
import numpy as np
from xai_sdk import Client
from xai_sdk.chat import user, system
import os
import json
from loguru import logger
import ta
from datetime import datetime

# 配置日誌
logger.add("logs/strategy_mastermind.log", rotation="1 MB")

class TechnicalAnalysis:
    def __init__(self):
        pass

    def backtest(self, symbol, data, timeframe='1d'):
        # 讀取歷史數據
        file_path = f"data/market/{timeframe}_{symbol.replace('^', '').replace('.', '_')}.csv"
        if not os.path.exists(file_path):
            logger.error(f"{symbol} {timeframe} 歷史數據檔案不存在: {file_path}")
            return {
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'expected_return': 0,
                'signals': {}
            }
        
        df = pd.read_csv(file_path)
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
        df['sma_20'] = ta.trend.SMAIndicator(df['close'], window=20).sma_indicator()
        
        # 簡單策略：RSI < 30 買入，RSI > 70 賣出
        df['signal'] = 0
        df.loc[df['rsi'] < 30, 'signal'] = 1  # 買入
        df.loc[df['rsi'] > 70, 'signal'] = -1  # 賣出
        
        # 計算回報和風險指標
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['returns'] * df['signal'].shift(1)
        sharpe_ratio = df['strategy_returns'].mean() / df['strategy_returns'].std() * np.sqrt(252) if timeframe == '1d' else np.sqrt(252 * 24)
        max_drawdown = (df['strategy_returns'].cumsum().cummax() - df['strategy_returns'].cumsum()).max()
        expected_return = df['strategy_returns'].mean() * (252 if timeframe == '1d' else 252 * 24)
        
        # 最新交易信號
        latest_close = df['close'].iloc[-1]
        multiplier = 1.05 if timeframe == '1d' else 1.02
        return {
            'sharpe_ratio': sharpe_ratio if not np.isnan(sharpe_ratio) else 0,
            'max_drawdown': max_drawdown if not np.isnan(max_drawdown) else 0,
            'expected_return': expected_return if not np.isnan(expected_return) else 0,
            'signals': {
                'position': 'LONG' if df['signal'].iloc[-1] == 1 else 'NEUTRAL' if df['signal'].iloc[-1] == 0 else 'SHORT',
                'entry_price': latest_close,
                'target_price': latest_close * multiplier,
                'stop_loss': latest_close * 0.95,
                'position_size': 0.5
            }
        }

class StrategyEngine:
    def __init__(self):
        self.models = {
            'technical': TechnicalAnalysis(),
            # 可擴展其他策略，如 RandomForestStrategy、LSTMStrategy
        }
        self.api_key = os.getenv("GROK_API_KEY")
        if not self.api_key:
            logger.error("XAI_API_KEY 未設置")
            raise EnvironmentError("XAI_API_KEY 未設置")

    def run_strategy_tournament(self, symbol, data, timeframe='1d'):
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
        prompt = f"""
為股票 {symbol} 選擇最佳策略（時間框架: {timeframe}）。以下是回測結果：
{json.dumps(results, ensure_ascii=False, indent=2)}
要求：
- 選擇夏普比率最高的策略，且最大回撤 < 15%。
- 提供最佳策略名稱、信心分數、預期回報、最大回撤、夏普比率和交易信號。
- 格式為 JSON:
```json
{{
  "symbol": "{symbol}",
  "analysis_date": "{datetime.today().strftime('%Y-%m-%d')}",
  "winning_strategy": {{
    "name": "strategy_name",
    "confidence": 0.0,
    "expected_return": 0.0,
    "max_drawdown": 0.0,
    "sharpe_ratio": 0.0
  }},
  "signals": {{
    "position": "LONG/NEUTRAL/SHORT",
    "entry_price": 0.0,
    "target_price": 0.0,
    "stop_loss": 0.0,
    "position_size": 0.0
  }}
}}
