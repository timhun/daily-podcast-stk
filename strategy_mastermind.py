import pandas as pd
import numpy as np
from xai_sdk import Client
from xai_sdk.chat import user, system
import os
from loguru import logger
import ta  # 技術分析庫
from datetime import datetime

# 配置日誌
logger.add("logs/strategy_mastermind.log", rotation="1 MB")

class TechnicalAnalysis:
    def __init__(self):
        pass

    def backtest(self, symbol, data):
        # 簡單技術分析策略：基於 RSI 和移動平均線
        df = pd.DataFrame([data], columns=['close', 'change'])
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
        df['sma_20'] = ta.trend.SMAIndicator(df['close'], window=20).sma_indicator()
        
        # 模擬回測結果
        return {
            'sharpe_ratio': 1.0,
            'max_drawdown': 0.1,
            'expected_return': 0.03,
            'signals': {'position': 'LONG', 'entry_price': data['close'], 'target_price': data['close'] * 1.05, 'stop_loss': data['close'] * 0.95, 'position_size': 0.5}
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
                results[name] = strategy.backtest(symbol, data)
                logger.info(f"{symbol} {name} 策略回測完成")
            except Exception as e:
                logger.error(f"{symbol} {name} 回測失敗: {str(e)}")
                results[name] = {'sharpe_ratio': 0, 'max_drawdown': 0, 'expected_return': 0, 'signals': {}}

        # 使用 Grok API 優化策略組合
        optimized = self.optimize_with_grok(symbol, results, timeframe)
        return optimized

    def optimize_with_grok(self, symbol, results):
        client = Client(api_key=self.api_key, timeout=3600)
        chat = client.chat.create(model="grok-3-mini")
        chat.append(system("You are an AI-driven financial strategy optimizer. Analyze strategy backtest results and select the best strategy based on Sharpe ratio, ensuring max drawdown < 15%."))

        prompt = f"""
        為股票 {symbol} 選擇最佳策略。以下是回測結果：
        {results}
        要求：
        - 選擇夏普比率最高的策略，且最大回撤 < 15%。
        - 提供最佳策略名稱、信心分數、預期回報、最大回撤、夏普比率和交易信號。
        - 格式為 JSON：
        {
          "symbol": "{symbol}",
          "analysis_date": "{datetime.today().strftime('%Y-%m-%d')}",
          "winning_strategy": {
            "name": "strategy_name",
            "confidence": 0.0,
            "expected_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0
          },
          "signals": {
            "position": "LONG/NEUTRAL/SHORT",
            "entry_price": 0.0,
            "target_price": 0.0,
            "stop_loss": 0.0,
            "position_size": 0.0
          }
        }
        """
        try:
            chat.append(user(prompt))
            response = chat.sample()
            optimized_result = json.loads(response.content)
            logger.info(f"{symbol} 策略優化完成: {optimized_result['winning_strategy']['name']}")
            return optimized_result
        except Exception as e:
            logger.error(f"{symbol} Grok API 優化失敗: {str(e)}")
            # 後備：選擇夏普比率最高的策略
            best_strategy = max(results.items(), key=lambda x: x[1]['sharpe_ratio'] if x[1].get('sharpe_ratio') else -float('inf'))
            return {
                'symbol': symbol,
                'analysis_date': datetime.today().strftime('%Y-%m-%d'),
                'winning_strategy': {
                    'name': best_strategy[0],
                    'confidence': 0.8,
                    'expected_return': best_strategy[1]['expected_return'],
                    'max_drawdown': best_strategy[1]['max_drawdown'],
                    'sharpe_ratio': best_strategy[1]['sharpe_ratio']
                },
                'signals': best_strategy[1]['signals']
            }