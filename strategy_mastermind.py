import json
import os
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from loguru import logger
from xai_sdk import Client
from xai_sdk.chat import user, system
from copy import deepcopy
from strategies.technical_strategy import TechnicalStrategy
from strategies.ml_strategy import MLStrategy
from strategies.bigline_strategy import BigLineStrategy
from strategies.simple_trend_strategy import SimpleTrendStrategy  # 新增
from strategies.utils import get_param_combinations

# 載入 config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 設置日誌
logger.add(config['logging']['file'], rotation=config['logging']['rotation'])

class StrategyEngine:
    def __init__(self):
        self.api_key = os.getenv("GROK_API_KEY")
        self.models = {}
        self._load_strategies()

    def _load_strategies(self):
        # 載入技術策略
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

        # 載入 ML 策略
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

        # 載入 BigLine 策略
        try:
            with open('strategies/bigline_strategy.json', 'r', encoding='utf-8') as f:
                bigline_params = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"載入 bigline_strategy.json 失敗: {str(e)}，使用預設參數")
            bigline_params = {
                "weights": [[0.4, 0.35, 0.25], [0.5, 0.3, 0.2], [0.3, 0.4, 0.3]],
                "ma_short": 5,
                "ma_mid": 20,
                "ma_long": 60,
                "vol_window": 60,
                "rsi_window": 14
            }
        self.models['bigline'] = BigLineStrategy(config, bigline_params)

        # 載入 SimpleTrend 策略
        try:
            with open('strategies/simple_trend_strategy.json', 'r', encoding='utf-8') as f:
                simple_trend_params = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"載入 simple_trend_strategy.json 失敗: {str(e)}，使用預設參數")
            simple_trend_params = {
                "ma_window": 20,
                "vol_window": 20,
                "breakout_price": 53.0,
                "min_data_length": 20
            }
        self.models['simple_trend'] = SimpleTrendStrategy(config, simple_trend_params)

    def _calculate_bigline(self, mode, data_dict):
        """計算台股或美股強化大盤線"""
        if mode == 'tw':
            index_symbol = '^TWII'
            components = ['2330.TW', '2454.TW', '2308.TW']
            weights = [0.4, 0.35, 0.25]  # 台股權重
        else:
            index_symbol = '^IXIC'
            components = ['NVDA', 'AAPL']
            weights = [0.6, 0.4]  # 美股權重

        try:
            # 載入大盤指數數據
            index_path = f"{config['data_paths']['market']}/daily_{index_symbol.replace('^', '').replace('.', '_')}.csv"
            index_df = pd.read_csv(index_path) if os.path.exists(index_path) else pd.DataFrame()
            if index_df.empty or 'close' not in index_df.columns:
                logger.warning(f"{index_symbol} 大盤數據無效")
                return None

            index_df['date'] = pd.to_datetime(index_df['date'])
            index_df.set_index('date', inplace=True)
            bigline = index_df['close'].copy()

            # 計算成分股加權平均
            for symbol, weight in zip(components, weights):
                if symbol in data_dict:
                    df = data_dict[symbol]
                    if not df.empty and 'close' in df.columns:
                        bigline += weight * df['close']
                    else:
                        logger.warning(f"{symbol} 數據無效，無法計算大盤線")
                else:
                    logger.warning(f"{symbol} 未提供數據，跳過大盤線計算")
                    return None

            return bigline
        except Exception as e:
            logger.error(f"計算 {mode} 大盤線失敗：{str(e)}")
            return None

    def _trend_analysis(self, symbol, data, mode):
        """趨勢分析，僅用於 ^IXIC 和 ^TWII"""
        if data.empty or 'close' not in data.columns:
            logger.error(f"{symbol} 數據無效或缺少 close 欄位")
            return {'trend': 'Unknown', 'rsi': 0.0}

        try:
            data['ma20'] = data['close'].rolling(window=20).mean()
            data['rsi'] = 100 - 100 / (1 + data['close'].pct_change().rolling(14).mean() / data['close'].pct_change().rolling(14).std())
            trend = 'Bullish' if data['close'].iloc[-1] > data['ma20'].iloc[-1] and data['ma20'].iloc[-1] > data['ma20'].iloc[-2] else 'Bearish'
            rsi = data['rsi'].iloc[-1] if not pd.isna(data['rsi'].iloc[-1]) else 0.0
            return {'trend': trend, 'rsi': rsi}
        except Exception as e:
            logger.error(f"{symbol} 趨勢分析失敗：{str(e)}")
            return {'trend': 'Unknown', 'rsi': 0.0}

    def run_strategy_tournament(self, symbol, data, mode, timeframe='daily'):
        """執行策略比賽，僅對 QQQ 和 0050.TW 生成買賣信號"""
        index_symbol = '^TWII' if mode == 'tw' else '^IXIC'
        trading_symbols = ['QQQ', '0050.TW']

        # 載入所有相關標的數據以計算大盤線
        data_dict = {symbol: data}
        for aux_symbol in config['symbols'][mode]:
            if aux_symbol != symbol:
                aux_path = f"{config['data_paths']['market']}/daily_{aux_symbol.replace('^', '').replace('.', '_').replace('-', '_')}.csv"
                data_dict[aux_symbol] = pd.read_csv(aux_path) if os.path.exists(aux_path) else pd.DataFrame()
                if not data_dict[aux_symbol].empty:
                    data_dict[aux_symbol]['date'] = pd.to_datetime(data_dict[aux_symbol]['date'])
                    data_dict[aux_symbol].set_index('date', inplace=True)

        # 計算大盤線
        bigline = self._calculate_bigline(mode, data_dict)

        # 趨勢分析（僅對 ^IXIC 和 ^TWII）
        if symbol in ['^IXIC', '^TWII']:
            logger.info(f"{symbol} 非主要交易標的，僅用於趨勢分析")
            return {
                'symbol': symbol,
                'analysis_date': datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d'),
                'index_symbol': index_symbol,
                'winning_strategy': {'name': 'none', 'confidence': 0.0, 'expected_return': 0.0, 'max_drawdown': 0.0, 'sharpe_ratio': 0.0},
                'signals': {'position': 'NEUTRAL', 'entry_price': 0.0, 'target_price': 0.0, 'stop_loss': 0.0, 'position_size': 0.0},
                'dynamic_params': {},
                'strategy_version': '2.0',
                'trend': self._trend_analysis(symbol, data, mode)
            }

        # 市場總結（僅對商品）
        if symbol in config['symbols']['commodities']:
            logger.info(f"{symbol} 用於市場總結播報")
            trend = self._trend_analysis(symbol, data, mode)
            return {
                'symbol': symbol,
                'analysis_date': datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d'),
                'index_symbol': index_symbol,
                'winning_strategy': {'name': 'none', 'confidence': 0.0, 'expected_return': 0.0, 'max_drawdown': 0.0, 'sharpe_ratio': 0.0},
                'signals': {'position': 'NEUTRAL', 'entry_price': 0.0, 'target_price': 0.0, 'stop_loss': 0.0, 'position_size': 0.0},
                'dynamic_params': {},
                'strategy_version': '2.0',
                'market_summary': {
                    'price': data['close'].iloc[-1] if not data.empty else 0.0,
                    'change': data['change'].iloc[-1] if not data.empty else 0.0,
                    'trend': trend['trend']
                }
            }

        # 買賣信號（僅對 QQQ 和 0050.TW）
        if symbol not in trading_symbols:
            logger.info(f"{symbol} 非主要交易標的，僅用於大盤線計算")
            return {
                'symbol': symbol,
                'analysis_date': datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d'),
                'index_symbol': index_symbol,
                'winning_strategy': {'name': 'none', 'confidence': 0.0, 'expected_return': 0.0, 'max_drawdown': 0.0, 'sharpe_ratio': 0.0},
                'signals': {'position': 'NEUTRAL', 'entry_price': 0.0, 'target_price': 0.0, 'stop_loss': 0.0, 'position_size': 0.0},
                'dynamic_params': {},
                'strategy_version': '2.0'
            }

        results = {}
        best_results = {}
        for name, strategy in self.models.items():
            best_score = -float('inf')
            best_params = None
            best_result = None
            param_combinations = get_param_combinations(strategy.params)
            for params in param_combinations:
                original_params = deepcopy(strategy.params)
                strategy.params = params
                try:
                    result = strategy.backtest(symbol, data, timeframe)
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
            best_results[name] = {'params': best_params, 'result': best_result}

        # 生成圖表（僅對 QQQ 和 0050.TW）
        if symbol in trading_symbols and bigline is not None and not data.empty:
            plt.figure(figsize=(10, 6))
            plt.plot(data.index, data['close'], label=f'{symbol} Price', color='blue')
            plt.plot(bigline.index, bigline, label=f'{mode.upper()} BigLine', color='orange')
            plt.title(f'{symbol} Price and {mode.upper()} BigLine')
            plt.xlabel('Date')
            plt.ylabel('Price', color='blue')
            plt.twinx()
            plt.ylabel('BigLine', color='orange')
            plt.legend()
            chart_dir = f"charts/{datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d')}"
            os.makedirs(chart_dir, exist_ok=True)
            plt.savefig(f"{chart_dir}/{symbol.replace('.', '_')}_daily.png")
            plt.close()
            logger.info(f"圖表儲存至：{chart_dir}/{symbol.replace('.', '_')}_daily.png")

        # 優化策略選擇
        optimized = self.optimize_with_grok(symbol, results, timeframe, best_results, index_symbol)
        if optimized is None:
            logger.error(f"{symbol} 優化結果為 None，返回預設結果")
            optimized = {
                'symbol': symbol,
                'analysis_date': datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d'),
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

        # 儲存策略結果
        strategy_dir = f"{config['data_paths']['strategy']}/{datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d')}"
        os.makedirs(strategy_dir, exist_ok=True)
        with open(f"{strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json", 'w', encoding='utf-8') as f:
            json.dump(optimized, f, ensure_ascii=False, indent=2)
        logger.info(f"策略結果儲存至: {strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json")

        return optimized

    def optimize_with_grok(self, symbol, results, timeframe, best_results, index_symbol):
        client = Client(api_key=self.api_key, timeout=3600)
        chat = client.chat.create(model="grok-3-mini")
        chat.append(system("You are an AI-driven financial strategy optimizer. Analyze strategy backtest results and select the best strategy based on expected return, ensuring max drawdown < 15%."))

        prompt = (
            f"為 {symbol} 選擇最佳策略（時間框架: {timeframe}，大盤參考: {index_symbol}）。以下是回測結果：\n"
            f"{json.dumps(results, ensure_ascii=False, indent=2)}\n"
            f"最佳參數：\n{json.dumps(best_results, ensure_ascii=False, indent=2)}\n"
            "要求：\n"
            f"- 選擇預期報酬最高的策略，且最大回撤 < {config['strategy_params']['max_drawdown_threshold']}。\n"
            "- 提供最佳策略名稱、信心分數、預期報酬、最大回撤、夏普比率、交易信號和動態參數。\n"
            "- 格式為 JSON:\n"
            "```json\n"
            "{\n"
            f'  "symbol": "{symbol}",\n'
            f'  "analysis_date": "{datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d')}",\n'
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
