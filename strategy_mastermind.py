import json
import os
from datetime import datetime
from loguru import logger
from xai_sdk import Client
from xai_sdk.chat import user, system
from copy import deepcopy
from strategies.technical_strategy import TechnicalStrategy
from strategies.ml_strategy import MLStrategy
from strategies.bigline_strategy import BigLineStrategy
from strategies.utils import get_param_combinations
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Configure logging
logger.add(config['logging']['file'], rotation=config['logging']['rotation'])

# 計算移動平均線
def calculate_ma(prices, window):
    return prices.rolling(window=window).mean()

# 判斷三線多頭
def is_bullish(ma_short, ma_mid, ma_long):
    return (ma_short > ma_mid) & (ma_mid > ma_long)

# 計算強化指數
def composite_index_with_weights(prices, volume, weight_stock_info, weights=[0.4, 0.35, 0.25]):
    ma_short = calculate_ma(prices, 5)
    ma_mid = calculate_ma(prices, 20)
    ma_long = calculate_ma(prices, 60)
    
    three_line_bullish = is_bullish(ma_short, ma_mid, ma_long)

    base_line = weights[0] * ma_short + weights[1] * ma_mid + weights[2] * ma_long

    max_vol = volume.rolling(window=60).max()
    vol_factor = 1 + (volume / (max_vol + 1e-9)) / 1e6  # 縮放成交量

    weighted_sum = 0
    for stock_name, info in weight_stock_info.items():
        bullish_binary = info['bullish'].astype(int)
        weighted_sum += info['alpha'] * bullish_binary * (info['weighted_ma'] / info['price'])

    final_index = base_line * vol_factor * (1 + weighted_sum)

    return pd.DataFrame({
        'Price': prices,
        'MA_5': ma_short,
        'MA_20': ma_mid,
        'MA_60': ma_long,
        'Three_Line_Bullish': three_line_bullish,
        'Base_Line': base_line,
        'Vol_Factor': vol_factor,
        'Weighted_Stock_Sum': weighted_sum,
        'Final_Index': final_index
    }, index=prices.index)

class StrategyEngine:
    def __init__(self):
        self.api_key = os.getenv("GROK_API_KEY")
        self.models = {}
        self._load_strategies()

    def _load_strategies(self):
        # Load technical strategy
        try:
            with open('strategies/technical_strategy.json', 'r', encoding='utf-8') as f:
                tech_params = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"載入 technical_strategy.json 失敗: {str(e)}，使用預設參數")
            tech_params = {
                "rsi_window": 14,
                "rsi_buy_threshold": 30,
                "rsi_sell_threshold": 70,
                "sma_window": 20,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
                "min_data_length_rsi_sma": 20
            }
        self.models['technical'] = TechnicalStrategy(config, tech_params)
        
        # Load ML strategy
        try:
            with open('strategies/ml_strategy.json', 'r', encoding='utf-8') as f:
                ml_params = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"載入 ml_strategy.json 失敗: {str(e)}，使用預設參數")
            ml_params = {
                "n_estimators": [50, 100, 200],
                "max_depth": [None, 10, 20],
                "rsi_window": 14,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
                "min_data_length": 50,
                "return_threshold": 0.01
            }
        self.models['ml'] = MLStrategy(config, ml_params)

        # Load BigLine strategy
        try:
            with open('strategies/bigline_strategy.json', 'r', encoding='utf-8') as f:
                bigline_params = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"載入 bigline_strategy.json 失敗: {str(e)}，使用預設參數")
            bigline_params = {
                "weights": [[0.4, 0.35, 0.25], [0.5, 0.3, 0.2], [0.3, 0.4, 0.3]],  # 多組權重以進行網格搜索
                "ma_short": 5,
                "ma_mid": 20,
                "ma_long": 60,
                "vol_window": 60,
                "rsi_window": 14
            }
        self.models['bigline'] = BigLineStrategy(config, bigline_params)

    def run_strategy_tournament(self, symbol, data, timeframe='daily', index_symbol=None):
        results = {}
        best_results = {}
        index_symbol = index_symbol or ('^TWII' if symbol in config['symbols']['tw'] else '^IXIC')
        index_file_path = f"{config['data_paths']['market']}/{timeframe}_{index_symbol.replace('^', '').replace('.', '_')}.csv"
        index_df = pd.read_csv(index_file_path) if os.path.exists(index_file_path) else pd.DataFrame()

        # 計算強化指數
        weight_stock_info = self._prepare_weight_stock_info(timeframe)
        composite_index_df = composite_index_with_weights(
            index_df['close'] if not index_df.empty else data['close'],
            index_df['volume'] if not index_df.empty else data['volume'],
            weight_stock_info
        )

        for name, strategy in self.models.items():
            best_score = -float('inf')
            best_params = None
            best_result = None

            # Load parameter combinations
            param_combinations = get_param_combinations(strategy.params)
            for params in param_combinations:
                original_params = deepcopy(strategy.params)
                strategy.params = params

                try:
                    # 將強化指數和情緒數據加入回測
                    strategy_data = data.copy()
                    strategy_data['composite_index'] = composite_index_df['Final_Index']
                    strategy_data['sentiment_score'] = self._load_sentiment_score(symbol, timeframe)
                    result = strategy.backtest(symbol, strategy_data, timeframe)
                    score = result['expected_return'] if result['max_drawdown'] < config['strategy_params']['max_drawdown_threshold'] else -float('inf')

                    if score > best_score:
                        best_score = score
                        best_params = params
                        best_result = result

                    logger.info(f"{symbol} {name} 策略參數 {params} 回測完成，Expected Return: {result['expected_return']:.4f}, Sharpe: {result['sharpe_ratio']:.2f}")
                except Exception as e:
                    logger.error(f"{symbol} {name} 參數 {params} 回測失敗: {str(e)}")
                finally:
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

        new_strategy = self._generate_dynamic_strategy(symbol, results, best_results, timeframe)
        if new_strategy:
            results['dynamic'] = self._apply_dynamic_strategy(symbol, new_strategy, timeframe)
            best_results['dynamic'] = {'params': new_strategy['parameters'], 'result': results['dynamic']}

        optimized = self.optimize_with_grok(symbol, results, timeframe, best_results, index_symbol)
        if optimized is None:
            logger.error(f"{symbol} 優化結果為 None，返回預設結果")
            optimized = {
                'symbol': symbol,
                'analysis_date': datetime.today().strftime('%Y-%m-%d'),
                'index_symbol': index_symbol,
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
                },
                'dynamic_params': {},
                'strategy_version': '2.0'
            }

        # 儲存強化指數圖表
        self._plot_composite_index(symbol, composite_index_df, timeframe)

        strategy_dir = f"{config['data_paths']['strategy']}/{datetime.today().strftime('%Y-%m-%d')}"
        os.makedirs(strategy_dir, exist_ok=True)
        with open(f"{strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json", 'w', encoding='utf-8') as f:
            json.dump(optimized, f, ensure_ascii=False, indent=2)
        logger.info(f"策略結果儲存至: {strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json")

        return optimized

    def _prepare_weight_stock_info(self, timeframe):
        weight_stock_info = {}
        for stock in ['0050.TW', '2330.TW']:
            file_path = f"{config['data_paths']['market']}/{timeframe}_{stock.replace('.', '_')}.csv"
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                
                price = df['close']
                ma_short = calculate_ma(price, 5)
                ma_mid = calculate_ma(price, 20)
                ma_long = calculate_ma(price, 60)
                bullish = is_bullish(ma_short, ma_mid, ma_long)
                weighted_ma = 0.4 * ma_short + 0.35 * ma_mid + 0.25 * ma_long
                
                weight_stock_info[stock] = {
                    'alpha': 0.3 if stock == '0050.TW' else 0.2,
                    'bullish': bullish,
                    'weighted_ma': weighted_ma,
                    'price': price
                }
            else:
                logger.warning(f"找不到 {stock} 的數據，使用模擬數據")
                dates = pd.date_range(start='2025-01-01', end='2025-09-09')
                price = pd.Series(1000 + np.random.normal(0, 5, len(dates)), index=dates)
                ma_short = calculate_ma(price, 5)
                ma_mid = calculate_ma(price, 20)
                ma_long = calculate_ma(price, 60)
                bullish = is_bullish(ma_short, ma_mid, ma_long)
                weighted_ma = 0.4 * ma_short + 0.35 * ma_mid + 0.25 * ma_long
                weight_stock_info[stock] = {
                    'alpha': 0.3 if stock == '0050.TW' else 0.2,
                    'bullish': bullish,
                    'weighted_ma': weighted_ma,
                    'price': price
                }
        return weight_stock_info

    def _plot_composite_index(self, symbol, composite_index_df, timeframe):
        fig, ax1 = plt.subplots(figsize=(14, 8))

        ax1.plot(composite_index_df.index, composite_index_df['Price'], label='台股加權指數', color='black')
        ax1.plot(composite_index_df.index, composite_index_df['MA_5'], label='5日均線', linestyle='--', color='#1f77b4')
        ax1.plot(composite_index_df.index, composite_index_df['MA_20'], label='20日均線', linestyle='--', color='#ff7f0e')
        ax1.plot(composite_index_df.index, composite_index_df['MA_60'], label='60日均線', linestyle='--', color='#2ca02c')
        ax1.fill_between(composite_index_df.index, composite_index_df['Price'].min(), composite_index_df['Price'].max(),
                         where=composite_index_df['Three_Line_Bullish'], color='lightgreen', alpha=0.3, label='三線多頭區間')
        ax1.set_xlabel('日期')
        ax1.set_ylabel('價格')
        ax1.legend(loc='upper left')
        ax1.grid(True)

        ax2 = ax1.twinx()
        ax2.plot(composite_index_df.index, composite_index_df['Final_Index'], label='強化大盤線', color='red', linewidth=2)
        ax2.set_ylabel('強化指數')
        ax2.legend(loc='upper right')

        plt.title(f'{symbol} 強化版大盤線與三線架構 ({timeframe})')
        chart_dir = f"charts/{datetime.today().strftime('%Y-%m-%d')}"
        os.makedirs(chart_dir, exist_ok=True)
        plt.savefig(f"{chart_dir}/{symbol.replace('.', '_')}_{timeframe}.png")
        plt.close()

    def _load_sentiment_score(self, symbol, timeframe):
        sentiment_file = f"{config['data_paths']['sentiment']}/{datetime.today().strftime('%Y-%m-%d')}/social_metrics.json"
        try:
            with open(sentiment_file, 'r', encoding='utf-8') as f:
                sentiment_data = json.load(f)
            return pd.Series(sentiment_data.get('symbols', {}).get(symbol, {}).get('sentiment_score', 0.0), index=pd.date_range(start='2025-01-01', end='2025-09-09'))
        except Exception as e:
            logger.error(f"載入情緒數據失敗: {str(e)}")
            return pd.Series(0.0, index=pd.date_range(start='2025-01-01', end='2025-09-09'))

    def _generate_dynamic_strategy(self, symbol, results, best_results, timeframe):
        best_expected_return = -float('inf')
        best_params = None
        for name, result in results.items():
            if result['expected_return'] > best_expected_return:
                best_expected_return = result['expected_return']
                best_params = best_results.get(name, {}).get('params', None)
        return {'parameters': best_params} if best_params else None

    def _apply_dynamic_strategy(self, symbol, strategy, timeframe):
        return {
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'expected_return': 0,
            'signals': {}
        }

    def optimize_with_grok(self, symbol, results, timeframe, best_results, index_symbol):
        client = Client(api_key=self.api_key, timeout=3600)
        chat = client.chat.create(model="grok-3-mini")
        chat.append(system("You are an AI-driven financial strategy optimizer. Analyze strategy backtest results and select the best strategy based on expected return, ensuring max drawdown < 15%."))

        prompt = (
            f"為股票 {symbol} 選擇最佳策略（時間框架: {timeframe}，大盤參考: {index_symbol}）。以下是回測結果：\n"
            f"{json.dumps(results, ensure_ascii=False, indent=2)}\n"
            f"最佳參數：\n{json.dumps(best_results, ensure_ascii=False, indent=2)}\n"
            "要求：\n"
            f"- 選擇預期報酬最高的策略，且最大回撤 < {config['strategy_params']['max_drawdown_threshold']}。\n"
            "- 提供最佳策略名稱、信心分數、預期報酬、最大回撤、夏普比率、交易信號和動態參數。\n"
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
            '  },\n'
            '  "dynamic_params": {},\n'
            '  "strategy_version": "2.0"\n'
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
