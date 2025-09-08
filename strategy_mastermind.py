import json
import os
from datetime import datetime
from loguru import logger
from xai_sdk import Client
from xai_sdk.chat import user, system
from copy import deepcopy
from strategies.technical_strategy import TechnicalStrategy
from strategies.ml_strategy import MLStrategy
from strategies.bigline_strategy import BigLineStrategy  # 新增匯入
from strategies.utils import get_param_combinations
import pandas as pd

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
                "max_depth": [null, 10, 20],
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
                "weights": [[0.4, 0.35, 0.25], [0.5, 0.3, 0.2], [0.3, 0.4, 0.3]],
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
                    result = strategy.backtest(symbol, data, timeframe)
                    score = result['expected_return']] if result['max_drawdown'] < config['strategy_params']['max_drawdown_threshold'] else -float('inf')

                    if score > best_score:
                        best_score = score
                        best_params = params
                        best_result = result

                    logger.info(f"{symbol} {name} 策略參數 {params} 回測完成，Sharpe: {result['sharpe_ratio']:.2f}")
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

        # Placeholder for dynamic strategy generation
        new_strategy = self._generate_dynamic_strategy(symbol, results, timeframe)
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

        strategy_dir = f"{config['data_paths']['strategy']}/{datetime.today().strftime('%Y-%m-%d')}"
        os.makedirs(strategy_dir, exist_ok=True)
        with open(f"{strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json", 'w', encoding='utf-8') as f:
            json.dump(optimized, f, ensure_ascii=False, indent=2)
        logger.info(f"策略結果儲存至: {strategy_dir}/{symbol.replace('^', '').replace('.', '_')}.json")

        return optimized

    def _generate_dynamic_strategy(self, symbol, results, timeframe):
        # 動態生成參數，選擇預期報酬最高的參數
        best_expected_return = -float('inf')
        best_params = None
        for name, result in results.items():
            if result['expected_return'] > best_expected_return:
                best_expected_return = result['expected_return']
                best_params = best_results[name]['params']
        return {'parameters': best_params} if best_params else None

    def _apply_dynamic_strategy(self, symbol, strategy, timeframe):
        # Placeholder for applying dynamic strategy
        return {
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'expected_return': 0,
            'signals': {}
        }

    def optimize_with_grok(self, symbol, results, timeframe, best_results, index_symbol):
        client = Client(api_key=self.api_key, timeout=3600)
        chat = client.chat.create(model="grok-3-mini")
        chat.append(system("You are an AI-driven financial strategy optimizer. Analyze strategy backtest results and select the best strategy based on Sharpe ratio, ensuring max drawdown < 15%."))

        prompt = (
            f"為股票 {symbol} 選擇最佳策略（時間框架: {timeframe}，大盤參考: {index_symbol}）。以下是回測結果：\n"
            f"{json.dumps(results, ensure_ascii=False, indent=2)}\n"
            f"最佳參數：\n{json.dumps(best_results, ensure_ascii=False, indent=2)}\n"
            "要求：\n"
            f"- 選擇預期報酬最高的策略，且最大回撤 < {config['strategy_params']['max_drawdown_threshold']}。\n"
            "- 提供最佳策略名稱、信心分數、預期回報、最大回撤、夏普比率、交易信號和動態參數。\n"
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
