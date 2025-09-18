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
import ta
import yfinance as yf  # For extended data
from threading import Thread  # For background optimization

# Conditional imports to handle missing packages
try:
    import google.generativeai as genai  # Gemini
except ImportError:
    genai = None
    logger.warning("google.generativeai not installed. Gemini unavailable.")
try:
    from groq import Groq  # Groq
except ImportError:
    Groq = None
    logger.warning("groq not installed. Groq unavailable.")

# Load config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Configure logging
logger.add(config['logging']['file'], rotation=config['logging']['rotation'])

# Calculate moving average
def calculate_ma(prices, window):
    if not isinstance(prices, pd.Series):
        raise ValueError(f"prices must be pandas.Series, got {type(prices)}")
    return prices.rolling(window=window, min_periods=1).mean()

# Check for three-line bullish pattern
def is_bullish(ma_short, ma_mid, ma_long):
    return (ma_short > ma_mid) & (ma_mid > ma_long)

# Calculate composite index
def composite_index_with_weights(prices, volume, weight_stock_info, weights=[0.4, 0.35, 0.25]):
    if not isinstance(prices, pd.Series) or not isinstance(volume, pd.Series):
        raise ValueError(f"prices and volume must be pandas.Series, got prices: {type(prices)}, volume: {type(volume)}")
    ma_short = calculate_ma(prices, 5)
    ma_mid = calculate_ma(prices, 20)
    ma_long = calculate_ma(prices, 60)
    
    three_line_bullish = is_bullish(ma_short, ma_mid, ma_long)

    base_line = weights[0] * ma_short + weights[1] * ma_mid + weights[2] * ma_long

    max_vol = volume.rolling(window=60, min_periods=1).max()
    vol_factor = 1 + (volume / (max_vol + 1e-9)) / 1e6  # Scale volume

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
            'bigline': BigLineStrategy
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
        """Run strategy backtests (unchanged logic, placeholder for original)"""
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
            best_results[name] = {'params': best_param_result['params']}

        optimized = self.optimize_with_grok(symbol, results, timeframe, best_results, index_symbol)
        if optimized:
            for name, strategy in self.models.items():
                if optimized['winning_strategy']['name'] == name:
                    strategy.params = optimized.get('dynamic_params', strategy.params)
        
        return results

    def optimize_all_strategies(self, strategy_results, mode, iterations=1, extended_data=False, background=True):
        """Optimize each strategy independently, optionally in background"""
        def _optimize_thread():
            data_period = config['ai_optimizer']['optimization']['weekend_data_period'] if extended_data else config['ai_optimizer']['optimization']['weekday_data_period']
            symbol = list(strategy_results.keys())[0]  # Use first symbol
            extended_df = self._load_extended_data(symbol, data_period)
            for name, strategy in self.models.items():
                logger.info(f"Optimizing {name} strategy ({iterations} iterations)...")
                for i in range(iterations):
                    optimized = self.optimize_with_ai(strategy_results.get(name, {}), name, extended_df)
                    if optimized:
                        strategy.params.update(optimized.get('dynamic_params', {}))
                        self._save_optimized_params(name, strategy.params)
                        logger.info(f"{name} iteration {i+1} optimized: {optimized['winning_strategy']}")

        if background:
            thread = Thread(target=_optimize_thread)
            thread.daemon = True
            thread.start()
            logger.info("Optimization running in background...")
        else:
            _optimize_thread()

    def _load_extended_data(self, symbol, period):
        """Load extended historical data, cache to CSV"""
        cache_path = f"{config['data_paths']['market']}/extended_{symbol.replace('^', '').replace('.', '_')}.csv"
        if os.path.exists(cache_path):
            df = pd.read_csv(cache_path)
            df['date'] = pd.to_datetime(df['date'])
            logger.info(f"Loaded cached extended data: {len(df)} rows")
            return df
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        if hist.empty:
            logger.warning(f"{symbol} extended data load failed")
            return None
        df = pd.DataFrame({
            'date': hist.index,
            'open': hist['Open'],
            'high': hist['High'],
            'low': hist['Low'],
            'close': hist['Close'],
            'volume': hist['Volume']
        })
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        df.to_csv(cache_path, index=False)
        logger.info(f"Extended data loaded and cached: {len(df)} rows")
        return df

    def _save_optimized_params(self, strategy_name, params):
        """Save optimized params"""
        path = f"{config['data_paths']['strategy']}/{strategy_name}_optimized.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(params, f, ensure_ascii=False, indent=2)
        logger.info(f"{strategy_name} optimized params saved to: {path}")

    def optimize_with_ai(self, results, strategy_name, extended_data=None):
        """General AI optimization, supports Grok/Gemini/Groq with fallback"""
        default_ai = self.ai_config.get('default_ai', 'grok')
        prompt = self._build_optimization_prompt(results, strategy_name, extended_data)

        if default_ai == 'grok':
            return self.optimize_with_grok(prompt)
        elif default_ai == 'gemini' and self.gemini_model:
            try:
                response = self.gemini_model.generate_content(prompt)
                return json.loads(response.text.strip('```json\n').strip('```\n'))
            except Exception as e:
                logger.error(f"Gemini optimization failed: {e}")
                return self.optimize_with_grok(prompt)
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
                return self.optimize_with_grok(prompt)
        else:
            logger.warning(f"No valid AI for {default_ai}, falling back to Grok")
            return self.optimize_with_grok(prompt)

    def _build_optimization_prompt(self, results, strategy_name, extended_data):
        """Build AI optimization prompt"""
        data_desc = f"using {len(extended_data)} rows of extended data" if extended_data is not None else "using existing data"
        prompt = (
            f"Optimize the {strategy_name} strategy ({data_desc}). Backtest results:\n"
            f"{json.dumps(results, ensure_ascii=False, indent=2)}\n"
            f"Requirements:\n"
            f"- Select the strategy with the highest expected return, ensuring max drawdown < {config['strategy_params']['max_drawdown_threshold']}.\n"
            f"- Focus on {strategy_name}-specific parameters (e.g., RSI thresholds for technical, n_estimators for ml).\n"
            f"- Provide the best strategy name, confidence, expected return, max drawdown, Sharpe ratio, trading signals, and dynamic parameters.\n"
            f"Output in JSON format:\n"
            "{\n"
            f'  "symbol": "{results.get('symbol', 'unknown')}",\n'
            f'  "analysis_date": "{datetime.today().strftime('%Y-%m-%d')}",\n'
            f'  "winning_strategy": {{\n'
            f'    "name": "{strategy_name}",\n'
            f'    "confidence": 0.0,\n'
            f'    "expected_return": 0.0,\n'
            f'    "max_drawdown": 0.0,\n'
            f'    "sharpe_ratio": 0.0\n'
            f'  }},\n'
            f'  "signals": {{\n'
            f'    "position": "LONG/NEUTRAL/SHORT",\n'
            f'    "entry_price": 0.0,\n'
            f'    "target_price": 0.0,\n'
            f'    "stop_loss": 0.0,\n'
            f'    "position_size": 0.0\n'
            f'  }},\n'
            f'  "dynamic_params": {{}},\n'
            f'  "strategy_version": "2.0"\n'
            f'}}'
        )
        return prompt

    def optimize_with_grok(self, prompt):
        """Grok optimization"""
        client = Client(api_key=self.api_key, timeout=3600)
        chat = client.chat.create(model="grok-3-mini")
        chat.append(system("You are an AI-driven financial strategy optimizer. Analyze strategy backtest results and select the best strategy based on expected return, ensuring max drawdown < 15%."))
        chat.append(user(prompt))
        response = chat.sample()
        try:
            optimized = json.loads(response.content.strip('```json\n').strip('```\n'))
            return optimized
        except json.JSONDecodeError:
            logger.error("Grok response JSON parsing failed")
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