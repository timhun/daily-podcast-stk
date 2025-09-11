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

class StrategyEngine:
    def __init__(self):
        self.api_key = os.getenv("GROK_API_KEY")
        self.models = {}
        self._load_strategies()

    def _load_strategies(self):
        # Technical Strategy
        try:
            with open('strategies/technical_strategy.json', 'r', encoding='utf-8') as f:
                tech_params = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load technical_strategy.json: {str(e)}, using default params")
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

        # ML Strategy
        try:
            with open('strategies/ml_strategy.json', 'r', encoding='utf-8') as f:
                ml_params = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load ml_strategy.json: {str(e)}, using default params")
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

        # BigLine Strategy (Trend-Following)
        try:
            with open('strategies/bigline_strategy.json', 'r', encoding='utf-8') as f:
                bigline_params = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load bigline_strategy.json: {str(e)}, using default params")
            bigline_params = {
                "ma_window": 20,
                "vol_window": 20,
                "breakout_price": 53.0,
                "min_data_length": 20
            }
        self.models['bigline'] = BigLineStrategy(config, bigline_params)

    def _trend_analysis(self, symbol, data, timeframe='daily'):
        if data.empty or len(data) < 20:
            logger.warning(f"{symbol} data insufficient for trend analysis")
            return {'trend': 'Unknown', 'rsi': 0.0}

        try:
            df = data.copy()
            df['MA20'] = df['close'].rolling(window=20).mean()
            df['RSI'] = 100 - (100 / (1 + (df['close'].diff().clip(lower=0) / df['close'].diff().clip(upper=0).abs()).rolling(window=14).mean()))
            trend = 'Bullish' if df['close'].iloc[-1] > df['MA20'].iloc[-1] and df['MA20'].iloc[-1] > df['MA20'].iloc[-2] else 'Bearish'
            rsi = df['RSI'].iloc[-1] if not df['RSI'].empty else 0.0
            return {'trend': trend, 'rsi': rsi}
        except Exception as e:
            logger.error(f"{symbol} trend analysis failed: {str(e)}")
            return {'trend': 'Unknown', 'rsi': 0.0}

    def run_strategy_tournament(self, symbol, data, timeframe='daily', index_symbol=None):
        index_symbol = index_symbol or ('^TWII' if symbol in config['symbols']['tw'] else '^IXIC')
        index_file_path = f"{config['data_paths']['market']}/{timeframe}_{index_symbol.replace('^', '').replace('.', '_')}.csv"
        index_df = pd.read_csv(index_file_path) if os.path.exists(index_file_path) else pd.DataFrame()

        # Non-trading symbols: trend analysis only
        if symbol not in ['QQQ', '0050.TW']:
            logger.info(f"{symbol} is not a trading symbol, performing trend analysis only")
            trend_result = self._trend_analysis(symbol, data, timeframe)
            return {
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
                'strategy_version': '2.0',
                'trend': trend_result['trend'],
                'rsi': trend_result['rsi']
            }

        # Trading symbols: run strategy tournament
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

                    logger.info(f"{symbol} {name} strategy params {params} backtest completed, Expected Return: {result['expected_return']:.4f}, Sharpe: {result['sharpe_ratio']:.2f}")
                except Exception as e:
                    logger.error(f"{symbol} {name} params {params} backtest failed: {str(e)}")
                finally:
                    strategy.params = original_params

            results[name] = best_result or {
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'expected_return': 0,
                'signals': {}
            }
            best_results[name] = {'params': best_params, 'result': best_result}

        new_strategy = self._generate_dynamic_strategy(symbol, results, best_results, timeframe)
        if new_strategy:
            results['dynamic'] = self._apply_dynamic_strategy(symbol, new_strategy, timeframe)
            best_results['dynamic'] = {'params': new_strategy['parameters'], 'result': results['dynamic']}

        optimized = self.optimize_with_grok(symbol, results, timeframe, best_results, index_symbol)
        if optimized is None:
            logger.error(f"{symbol} optimization returned None, using default results")
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

        strategy_dir = f"{config['data_paths']['strategy']}/{datetime.today().strftime('%Y-%m-%d')}"
        os.makedirs(strategy_dir, exist_ok=True)
        with open(f"{strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json", 'w', encoding='utf-8') as f:
            json.dump(optimized, f, ensure_ascii=False, indent=2)
        logger.info(f"Strategy results saved to: {strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json")

        return optimized

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
            f"Select the best strategy for {symbol} (timeframe: {timeframe}, index: {index_symbol}). Backtest results:\n"
            f"{json.dumps(results, ensure_ascii=False, indent=2)}\n"
            f"Best parameters:\n{json.dumps(best_results, ensure_ascii=False, indent=2)}\n"
            "Requirements:\n"
            f"- Choose the strategy with the highest expected return and max drawdown < {config['strategy_params']['max_drawdown_threshold']}.\n"
            "- Provide strategy name, confidence, expected return, max drawdown, sharpe ratio, signals, and dynamic params.\n"
            "- Format as JSON:\n"
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
            logger.error("Grok response JSON parsing failed")
            return None