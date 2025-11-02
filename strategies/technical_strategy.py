import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
from .utils import generate_performance_chart
import ta
from loguru import logger
import json
import datetime


class TechnicalStrategy(BaseStrategy):
    def __init__(self, config, params=None):
        super().__init__(config, params)
        if not params:
            try:
                with open('strategies/technical_strategy.json', 'r', encoding='utf-8') as f:
                    self.params = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load technical_strategy.json: {str(e)}, using default params")
                self.params = {
                    "rsi_window": 14,
                    "rsi_buy_threshold": 30,
                    "rsi_sell_threshold": 70,
                    "sma_window": 20,
                    "macd_fast": 12,  # 預設值
                    "macd_slow": 26,  # 預設值
                    "macd_signal": 9,  # 預設值
                    "min_data_length_rsi_sma": 20
                }
    def optimize(self, symbol, timeframe, period='1y', max_iterations=3):
        """獨立優化：生成參數組合，回測，AI選擇最佳"""
        # 載入長資料
        df = self.load_data(symbol, timeframe, period=period)  # 修改load_data支援period
        if df is None or len(df) < 50:
            return None

        # 生成參數組合（使用utils.get_param_combinations）
        param_combos = get_param_combinations(self.params, num_combos=5 if self.is_weekday() else 10)  # 平日5, 假日10

        backtest_results = {}
        for params in param_combos:
            temp_strategy = TechnicalStrategy(self.config, params)  # 臨時實例
            result = temp_strategy.backtest(symbol, df, timeframe)
            backtest_results[str(params)] = result

        # AI迭代優化（3-5輪）
        best_params = self._ai_optimize(backtest_results, max_iterations)
        return {'parameters': best_params}

    def _ai_optimize(self, results, max_iterations):
        """使用Grok/Gemini/Claude迭代選擇最佳params"""
        current_best = max(results.items(), key=lambda x: x[1]['expected_return'])
        for i in range(max_iterations):
            prompt = f"基於回測結果 {json.dumps(results)}，優化technical策略參數 (RSI window/thresholds等)。當前最佳: {current_best}。建議新組合: JSON格式 {{'rsi_window': int, 'rsi_buy_threshold': int, ...}}"

            # 輪詢AI
            ais = ['grok', 'gemini', 'groq']
            suggestions = []
            for ai in ais:
                if ai == 'grok' and self.api_key:
                    # Grok prompt (類似原有optimize_with_grok)
                    client = Client(api_key=self.api_key)
                    chat = client.chat.create(model="grok-3-mini")
                    chat.append(system("You are a strategy optimizer. Suggest improved params."))
                    chat.append(user(prompt))
                    response = chat.sample().content
                    try:
                        suggestion = json.loads(response)
                        suggestions.append(suggestion)
                    except:
                        pass
                elif ai == 'gemini' and self.gemini_key:
                    model = genai.GenerativeModel('gemini-pro')
                    response = model.generate_content(prompt)
                    try:
                        suggestion = json.loads(response.text)
                        suggestions.append(suggestion)
                    except:
                        pass
                elif ai == 'groq' and self.groq_client:
                    response = self.groq_client.messages.create(
                        model="openai/gpt-oss-20b",
                        max_tokens=1000,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    try:
                        suggestion = json.loads(response.content[0].text)
                        suggestions.append(suggestion)
                    except:
                        pass

            # 選擇平均/投票最佳
            if suggestions:
                # 簡單平均 (可擴展)
                avg_params = {k: np.mean([s.get(k, 0) for s in suggestions]) for k in set().union(*[s.keys() for s in suggestions])}
                current_best = avg_params  # 更新

        return current_best
    
    def _load_sentiment_score(self, symbol, timeframe):
        sentiment_file = f"{self.config['data_paths']['sentiment']}/{datetime.today().strftime('%Y-%m-%d')}/social_metrics.json"
        try:
            with open(sentiment_file, 'r', encoding='utf-8') as f:
                sentiment_data = json.load(f)
            score = sentiment_data.get('symbols', {}).get(symbol, {}).get('sentiment_score', 0.0)
            logger.info(f"{symbol} 情緒分數: {score}")
            return score
        except Exception as e:
            logger.error(f"載入 {symbol} 情緒數據失敗: {str(e)}")
            return 0.0

    def backtest(self, symbol, data, timeframe='daily'):
        df = self.load_data(symbol, timeframe)
        if df is None:
            return self._default_results()


        if symbol not in ['QQQ', '0050.TW']:
            logger.info(f"{symbol} 非主要交易標的，跳過回測")
            return self._default_results()
            
        try:
            # 確保參數存在
            macd_fast = self.params.get('macd_fast', 12)
            macd_slow = self.params.get('macd_slow', 26)
            macd_signal = self.params.get('macd_signal', 9)
            rsi_window = self.params.get('rsi_window', 14)
            rsi_buy_threshold = self.params.get('rsi_buy_threshold', 30)
            rsi_sell_threshold = self.params.get('rsi_sell_threshold', 70)
            sma_window = self.params.get('sma_window', 20)
            min_data_length = self.params.get('min_data_length_rsi_sma', 20)

            if len(df) < min_data_length:
                logger.warning(f"{symbol} data insufficient or empty")
                return self._default_results()

            # Calculate technical indicators
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=rsi_window).rsi()
            df['sma_20'] = ta.trend.SMAIndicator(df['close'], window=sma_window).sma_indicator()
            df['macd'] = ta.trend.MACD(df['close'], window_fast=macd_fast, window_slow=macd_slow, window_sign=macd_signal).macd()
            df['macd_signal'] = ta.trend.MACD(df['close'], window_fast=macd_fast, window_slow=macd_slow, window_sign=macd_signal).macd_signal()
            df['bollinger_hband'] = ta.volatility.BollingerBands(df['close']).bollinger_hband()
            df['bollinger_lband'] = ta.volatility.BollingerBands(df['close']).bollinger_lband()
            sentiment_score = self._load_sentiment_score(symbol, timeframe)

            # Generate signals
            df['signal'] = 0
            df.loc[(df['rsi'] < rsi_buy_threshold) &
                   (df['macd'] > df['macd_signal']) &
                   (df['close'] <= df['bollinger_lband']) &
                   (sentiment_score > 0.5), 'signal'] = 1
            df.loc[(df['rsi'] > rsi_sell_threshold) &
                   (df['macd'] < df['macd_signal']) &
                   (df['close'] >= df['bollinger_hband']) &
                   (sentiment_score < -0.5), 'signal'] = -1

            # Calculate returns
            df['returns'] = df['close'].pct_change()
            df['strategy_returns'] = df['returns'] * df['signal'].shift(1)
            sharpe_ratio = df['strategy_returns'].mean() / df['strategy_returns'].std() * np.sqrt(
                self.config['strategy_params']['sharpe_annualization_daily'] if timeframe == 'daily' else self.config['strategy_params']['sharpe_annualization_hourly']
            ) if df['strategy_returns'].std() != 0 else 0
            max_drawdown = (df['strategy_returns'].cumsum().cummax() - df['strategy_returns'].cumsum()).max()
            expected_return = df['strategy_returns'].mean() * (
                self.config['strategy_params']['expected_return_annualization_daily'] if timeframe == 'daily' else self.config['strategy_params']['expected_return_annualization_hourly']
            )

            # Generate signals
            latest_close = df['close'].iloc[-1]
            multiplier = self.config['strategy_params']['daily_multiplier'] if timeframe == 'daily' else self.config['strategy_params']['hourly_multiplier']
            signals = {
                'position': 'LONG' if df['signal'].iloc[-1] == 1 else 'NEUTRAL' if df['signal'].iloc[-1] == 0 else 'SHORT',
                'entry_price': latest_close,
                'target_price': latest_close * multiplier,
                'stop_loss': latest_close * self.config['strategy_params']['stop_loss_ratio'],
                'position_size': self.config['strategy_params']['position_size']
            }

            # Generate performance chart
            chart_url = generate_performance_chart(df, symbol, timeframe)

            return {
                'sharpe_ratio': sharpe_ratio if not np.isnan(sharpe_ratio) else 0,
                'max_drawdown': max_drawdown if not np.isnan(max_drawdown) else 0,
                'expected_return': expected_return if not np.isnan(expected_return) else 0,
                'signals': signals,
                'chart_url': chart_url
            }
        except Exception as e:
            logger.error(f"{symbol} {timeframe} 回測失敗: {str(e)}")
            return self._default_results()
