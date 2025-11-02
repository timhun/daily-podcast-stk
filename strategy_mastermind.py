import json
import os
from datetime import datetime
from loguru import logger
from scripts.grok_api import ask_grok_json
from copy import deepcopy
from strategies.technical_strategy import TechnicalStrategy
from strategies.ml_strategy import MLStrategy
from strategies.bigline_strategy import BigLineStrategy
from strategies.god_system_strategy import GodSystemStrategy
from strategies.utils import get_param_combinations
from config import get_market_data_path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import ta
import yfinance as yf
from threading import Thread
import schedule
import time

try:
    import google.generativeai as genai
except ImportError:
    genai = None
    logger.warning("google.generativeai not installed. Gemini unavailable.")
try:
    from groq import Groq
except ImportError:
    Groq = None
    logger.warning("groq not installed. Groq unavailable.")

# Load config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Configure logging
logger.add(config['logging']['file'], rotation=config['logging']['rotation'])

class StrategyEngine:
    def __init__(self):
        self.api_key = os.getenv("GROK_API_KEY")
        self.models = {}
        self.ai_config = config.get('ai_optimizer', {'default_ai': 'grok'})
        self.gemini_model = None
        self.groq_client = None
        self._load_strategies()
        self._init_ai_clients()

    def _load_strategies(self):
        """Load strategies, prioritize optimized params"""
        strategy_classes = {
            'technical': TechnicalStrategy,
            'ml': MLStrategy,
            'bigline': BigLineStrategy,
            'god_system': GodSystemStrategy
        }
        for name, strategy_class in strategy_classes.items():
            optimized_path = f"{config['data_paths']['strategy']}/{name}_optimized.json"
            params = self._load_json_params(optimized_path) or self._load_default_params(name)
            strategy = strategy_class(config, params)
            self.models[name] = strategy
            logger.info(f"{name} strategy loaded (optimized params: {os.path.exists(optimized_path)})")

    def _load_default_params(self, name):
        """Load default params"""
        try:
            with open(f'strategies/{name}_strategy.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error(f"Failed to load {name}_strategy.json, using default params")
            if name == 'god_system':
                return {
                    "ma_month": 20
                }
            return {}

    def _load_json_params(self, path):
        """Load JSON params"""
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in {path}: {e}")
        return None

    def _init_ai_clients(self):
        """Initialize AI clients with fallback"""
        default_ai = self.ai_config.get('default_ai', 'grok')
        if default_ai == 'gemini' and genai is not None:
            try:
                genai.configure(api_key=os.getenv('GEMINI_API_KEY') or self.ai_config['api_keys'].get('gemini'))
                self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("Gemini AI client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.gemini_model = None
        elif default_ai == 'groq' and Groq is not None:
            try:
                self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY') or self.ai_config['api_keys'].get('groq'))
                logger.info("Groq AI client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Groq: {e}")
                self.groq_client = None
        else:
            logger.info("Defaulting to Grok AI client")

    def run_strategy_tournament(self, symbol, data, timeframe='daily', index_symbol=None):
        """Run strategy backtests"""
        results = {}
        best_results = {}
        index_symbol = index_symbol or ('^TWII' if symbol == '0050.TW' else '^IXIC')
        
        for name, strategy in self.models.items():
            param_combinations = get_param_combinations(strategy.params)
            best_score = -float('inf')
            best_param_result = None
            
            for params in param_combinations:
                strategy.params = params
                result = strategy.backtest(symbol, data, timeframe)
                score = result.get('expected_return', 0) / (result.get('max_drawdown', 1) + 1e-9)
                if score > best_score:
                    best_score = score
                    best_param_result = result
                    best_param_result['params'] = params
            
            results[name] = best_param_result
            best_results[name] = best_param_result
            logger.info(f"{name} strategy for {symbol}: Sharpe={best_param_result['sharpe_ratio']:.2f}, "
                       f"Max Drawdown={best_param_result['max_drawdown']:.2f}, "
                       f"Expected Return={best_param_result['expected_return']:.2f}")
        
        return results

    def daily_backtest(self, mode='tw'):
        """Run daily backtest for all strategies using data from data_collector"""
        logger.info(f"執行每日回測 for {mode} at {datetime.now()}")
        symbols = config['symbols'][mode]
        
        for symbol in symbols:
            try:
                csv_file = get_market_data_path(symbol, 'daily')
                daily_df = pd.read_csv(csv_file)
                daily_df['date'] = pd.to_datetime(daily_df['date'])
                daily_df.set_index('date', inplace=True)
                logger.info(f"Successfully loaded data for {symbol} from {csv_file}")
            except FileNotFoundError:
                logger.error(f"Data file not found for {symbol} at {csv_file}, skipping backtest.")
                continue
            except Exception as e:
                logger.error(f"Failed to load data for {symbol}: {str(e)}")
                continue

            results = self.run_strategy_tournament(symbol, daily_df, timeframe='daily')
            
            if 'god_system' in results:
                god_result = results['god_system']
                logger.info(f"GodSystemStrategy for {symbol}: "
                           f"Sharpe={god_result['sharpe_ratio']:.2f}, "
                           f"Max Drawdown={god_result['max_drawdown']:.2f}, "
                           f"Expected Return={god_result['expected_return']:.2f}, "
                           f"Signal={god_result['signals']['position']}")

    def optimize_with_ai(self, results, strategy_name, extended_data=None):
        """General AI optimization, supports Grok/Gemini/Groq with fallback"""")

    def optimize_with_ai(self, results, strategy_name, extended_data=None):
        """General AI optimization, supports Grok/Gemini/Groq with fallback"""
        default_ai = self.ai_config.get('default_ai', 'grok')
        prompt = self._build_optimization_prompt(results, strategy_name, extended_data)

        if default_ai == 'gemini' and self.gemini_model:
            try:
                response = self.gemini_model.generate_content(prompt)
                return json.loads(response.text.strip('```json\n').strip('```\n'))
            except Exception as e:
                logger.error(f"Gemini optimization failed: {e}")
                return self.optimize_with_grok(symbol=results.get('symbol', 'unknown'), results=results, timeframe='daily', best_results=results, index_symbol='^TWII')
        elif default_ai == 'groq' and self.groq_client:
            try:
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama3-8b-8192",
                    temperature=0.7
                )
                response_text = chat_completion.choices[0].message.content
                return json.loads(response_text.strip('```json\n').strip('```\n'))
            except Exception as e:
                logger.error(f"Groq optimization failed: {e}")
                return self.optimize_with_grok(symbol=results.get('symbol', 'unknown'), results=results, timeframe='daily', best_results=results, index_symbol='^TWII')
        else:
            logger.warning(f"No valid AI for {default_ai}, falling back to Grok")
            return self.optimize_with_grok(symbol=results.get('symbol', 'unknown'), results=results, timeframe='daily', best_results=results, index_symbol='^TWII')

    def _build_optimization_prompt(self, results, strategy_name, extended_data):
        """Build AI optimization prompt"""
        data_desc = f"using {len(extended_data)} rows of extended data" if extended_data is not None else "using existing data"
        symbol = results.get('symbol', 'unknown')
        prompt_parts = [
            f"Optimize the {strategy_name} strategy ({data_desc}).",
            f"Backtest results:\n{json.dumps(results, ensure_ascii=False, indent=2)}",
            f"Requirements:",
            f"- Select the strategy with the highest expected return, ensuring max drawdown < {config['strategy_params']['max_drawdown_threshold']}.",
            f"- Focus on {strategy_name}-specific parameters (e.g., ma_month for god_system).",
            f"- Provide the best strategy name, confidence, expected return, max drawdown, Sharpe ratio, trading signals, and dynamic parameters.",
            f"Output in JSON format:",
            '{',
            f'  "symbol": "{symbol}",',
            f'  "analysis_date": "{datetime.today().strftime("%Y-%m-%d")}",',
            f'  "winning_strategy": {{',
            f'    "name": "{strategy_name}",',
            f'    "confidence": 0.0,',
            f'    "expected_return": 0.0,',
            f'    "max_drawdown": 0.0,',
            f'    "sharpe_ratio": 0.0',
            f'  }},',
            f'  "signals": {{',
            f'    "position": "LONG/NEUTRAL/SHORT",',
            f'    "entry_price": 0.0,',
            f'    "target_price": 0.0,',
            f'    "stop_loss": 0.0,',
            f'    "position_size": 0.0',
            f'  }},',
            f'  "dynamic_params": {{}},',
            f'  "strategy_version": "2.0"',
            f'}}'
        ]
        prompt = '\n'.join(prompt_parts)
        logger.debug(f"Generated optimization prompt for {strategy_name}:\n{prompt}")
        return prompt

    def optimize_with_grok(self, symbol, results, timeframe, best_results, index_symbol):
        """Grok optimization via HTTP helper returning parsed JSON"""
        prompt_lines = [
            f"Select the best strategy for {symbol} (timeframe: {timeframe}, index: {index_symbol}).",
            f"Backtest results:\n{json.dumps(results, ensure_ascii=False, indent=2)}",
            f"Best parameters:\n{json.dumps(best_results, ensure_ascii=False, indent=2)}",
            "Requirements:",
            f"- Select the strategy with the highest expected return, max drawdown < {config['strategy_params']['max_drawdown_threshold']}.",
            "- Provide best strategy name, confidence, expected return, max drawdown, Sharpe ratio, trading signals, and dynamic parameters.",
            "Output in strictly valid JSON format:",
            '{',
            f'  "symbol": "{symbol}",',
            f'  "analysis_date": "{datetime.today().strftime("%Y-%m-%d")}",',
            f'  "index_symbol": "{index_symbol}",',
            '  "winning_strategy": {',
            '    "name": "strategy_name",',
            '    "confidence": 0.0,',
            '    "expected_return": 0.0,',
            '    "max_drawdown": 0.0,',
            '    "sharpe_ratio": 0.0',
            '  },',
            '  "signals": {',
            '    "position": "LONG/NEUTRAL/SHORT",',
            '    "entry_price": 0.0,',
            '    "target_price": 0.0,',
            '    "stop_loss": 0.0,',
            '    "position_size": 0.0',
            '  },',
            '  "dynamic_params": {},',
            '  "strategy_version": "2.0"',
            '}'
        ]
        prompt = '\n'.join(prompt_lines)
        try:
            optimized = ask_grok_json(prompt, role="user", model=os.getenv("GROK_MODEL", "grok-4"))
            return optimized
        except Exception as e:
            logger.error(f"Grok optimization failed: {e}")
            return None

    def _get_best_strategy_params(self, best_results):
        """Get best strategy parameters"""
        name = max(best_results, key=lambda k: best_results[k].get('expected_return', 0))
        best_params = best_results.get(name, {}).get('params', None)
        return {'parameters': best_params} if best_params else None

    def _apply_dynamic_strategy(self, symbol, strategy, timeframe):
        """Apply dynamic strategy (placeholder)"""
        return {
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'expected_return': 0,
            'signals': {}
        }

# Scheduling for daily backtest
def run_daily_backtest():
    engine = StrategyEngine()
    engine.daily_backtest(mode='tw')
    logger.info("Daily backtest completed")

if __name__ == "__main__":
    schedule.every().day.at("14:00").do(run_daily_backtest)
    logger.info("Starting daily backtest schedule")
    while True:
        schedule.run_pending()
        time.sleep(60)
