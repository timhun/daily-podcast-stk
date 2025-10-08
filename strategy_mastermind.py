import json
import os
from datetime import datetime
from loguru import logger
from copy import deepcopy
from strategies.technical_strategy import TechnicalStrategy
from strategies.ml_strategy import MLStrategy
from strategies.bigline_strategy import BigLineStrategy
from strategies.utils import get_param_combinations
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import ta
import yfinance as yf
from threading import Thread

# Conditional imports

try:
import google.generativeai as genai
except ImportError:
genai = None
logger.warning(“google.generativeai not installed. Gemini unavailable.”)

try:
from groq import Groq
except ImportError:
Groq = None
logger.warning(“groq not installed. Groq unavailable.”)

# FIX #1: Handle missing grok_api gracefully

try:
from grok_api import ask_grok_json
GROK_AVAILABLE = True
except ImportError:
logger.warning(“grok_api not installed. Grok unavailable.”)
GROK_AVAILABLE = False
ask_grok_json = None

# Load config.json

with open(‘config.json’, ‘r’, encoding=‘utf-8’) as f:
config = json.load(f)

# Configure logging

logger.add(config[‘logging’][‘file’], rotation=config[‘logging’][‘rotation’])

def calculate_ma(prices, window):
“”“Calculate moving average with proper error handling”””
if not isinstance(prices, pd.Series):
raise ValueError(f”prices must be pandas.Series, got {type(prices)}”)
if len(prices) < window:
logger.warning(f”Price data length {len(prices)} < window {window}”)
return prices.rolling(window=window, min_periods=1).mean()

def is_bullish(ma_short, ma_mid, ma_long):
“”“Check for three-line bullish pattern”””
return (ma_short > ma_mid) & (ma_mid > ma_long)

def composite_index_with_weights(prices, volume, weight_stock_info, weights=[0.4, 0.35, 0.25]):
“”“Calculate composite index with proper validation”””
if not isinstance(prices, pd.Series) or not isinstance(volume, pd.Series):
raise ValueError(
f”prices and volume must be pandas.Series, “
f”got prices: {type(prices)}, volume: {type(volume)}”
)

```
# Validate weights
if len(weights) != 3 or not np.isclose(sum(weights), 1.0):
    logger.warning(f"Weights {weights} should sum to 1.0, normalizing...")
    weights = np.array(weights) / sum(weights)

ma_short = calculate_ma(prices, 5)
ma_mid = calculate_ma(prices, 20)
ma_long = calculate_ma(prices, 60)

three_line_bullish = is_bullish(ma_short, ma_mid, ma_long)
base_line = weights[0] * ma_short + weights[1] * ma_mid + weights[2] * ma_long

max_vol = volume.rolling(window=60, min_periods=1).max()
vol_factor = 1 + (volume / (max_vol + 1e-9)) / 1e6

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
```

class StrategyEngine:
ALLOWED_SYMBOLS = {‘QQQ’, ‘0050.TW’}

```
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

def _load_default_params(self, name):
    """Load default params with better error handling"""
    try:
        with open(f'strategies/{name}_strategy.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Default params file not found: {name}_strategy.json")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {name}_strategy.json: {e}")
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
            api_key = os.getenv('GEMINI_API_KEY') or self.ai_config.get('api_keys', {}).get('gemini')
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found")
            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Gemini AI client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.gemini_model = None
            
    elif default_ai == 'groq' and Groq is not None:
        try:
            api_key = os.getenv('GROQ_API_KEY') or self.ai_config.get('api_keys', {}).get('groq')
            if not api_key:
                raise ValueError("GROQ_API_KEY not found")
            self.groq_client = Groq(api_key=api_key)
            logger.info("Groq AI client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Groq: {e}")
            self.groq_client = None
            
    elif default_ai == 'grok':
        if GROK_AVAILABLE and self.api_key:
            logger.info("Grok AI client initialized")
        else:
            logger.warning("Grok unavailable: check grok_api import and GROK_API_KEY")

def run_strategy_tournament(self, symbol, data, timeframe='daily', index_symbol=None):
    """Run strategy backtests for allowed symbols only"""
    if symbol not in self.ALLOWED_SYMBOLS:
        logger.info(f"Symbol {symbol} not in allowed list, skipping tournament")
        return {}
    
    results = {}
    best_results = {}
    index_symbol = index_symbol or ('^TWII' if symbol == '0050.TW' else '^IXIC')
    
    logger.info(f"Running strategy tournament for {symbol}")
    
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
        
        if best_param_result:
            results[name] = best_param_result
            best_results[name] = {'params': best_param_result['params']}
    
    # FIX #2: Pass symbol explicitly to optimize_with_grok
    optimized = self._optimize_tournament_results(symbol, results, timeframe, best_results, index_symbol)
    
    if optimized and 'winning_strategy' in optimized:
        winning_name = optimized['winning_strategy'].get('name')
        if winning_name in self.models:
            self.models[winning_name].params = optimized.get('dynamic_params', self.models[winning_name].params)
    
    return results

def _optimize_tournament_results(self, symbol, results, timeframe, best_results, index_symbol):
    """Wrapper for tournament optimization with better error handling"""
    try:
        if GROK_AVAILABLE and self.api_key:
            return self.optimize_with_grok(symbol, results, timeframe, best_results, index_symbol)
        else:
            logger.warning("Grok unavailable, skipping tournament optimization")
            return None
    except Exception as e:
        logger.error(f"Tournament optimization failed: {e}")
        return None

def optimize_all_strategies(self, strategy_results, mode, iterations=1, extended_data=False, background=True):
    """Optimize each strategy independently for allowed symbols"""
    def _optimize_thread():
        data_period = (
            config['optimization']['weekend_data_period'] if extended_data 
            else config['optimization']['weekday_data_period']
        )
        
        if not strategy_results:
            logger.warning("No strategy_results provided for optimization")
            return
        
        for symbol, sym_results in strategy_results.items():
            if symbol not in self.ALLOWED_SYMBOLS:
                logger.info(f"Symbol {symbol} not in allowed list, skipping optimization")
                continue
            
            logger.info(f"Starting optimization for {symbol}")
            extended_df = self._load_extended_data(symbol, data_period)
            
            for name, strategy in self.models.items():
                logger.info(f"Optimizing {name} strategy ({iterations} iterations)...")
                for i in range(iterations):
                    # FIX #3: Pass symbol and strategy_name correctly
                    optimized = self.optimize_with_ai(
                        symbol=symbol,
                        results=sym_results,
                        strategy_name=name,
                        extended_data=extended_df
                    )
                    if optimized and 'dynamic_params' in optimized:
                        strategy.params.update(optimized['dynamic_params'])
                        self._save_optimized_params(name, strategy.params)

    if background:
        thread = Thread(target=_optimize_thread)
        thread.daemon = True
        thread.start()
    else:
        _optimize_thread()

def _load_extended_data(self, symbol, period):
    """Load extended historical data with caching"""
    cache_path = f"{config['data_paths']['market']}/extended_{symbol.replace('^', '').replace('.', '_')}.csv"
    
    if os.path.exists(cache_path):
        try:
            df = pd.read_csv(cache_path)
            df['date'] = pd.to_datetime(df['date'])
            logger.info(f"Loaded cached data for {symbol}")
            return df
        except Exception as e:
            logger.warning(f"Failed to load cached data: {e}, fetching fresh data")
    
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            logger.warning(f"No historical data for {symbol}")
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
        logger.info(f"Cached extended data for {symbol}")
        return df
        
    except Exception as e:
        logger.error(f"Failed to fetch extended data for {symbol}: {e}")
        return None

def _save_optimized_params(self, strategy_name, params):
    """Save optimized params"""
    path = f"{config['data_paths']['strategy']}/{strategy_name}_optimized.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(params, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved optimized params for {strategy_name}")
    except Exception as e:
        logger.error(f"Failed to save optimized params for {strategy_name}: {e}")

def optimize_with_ai(self, symbol, results, strategy_name, extended_data=None):
    """General AI optimization with proper fallback chain"""
    default_ai = self.ai_config.get('default_ai', 'grok')
    prompt = self._build_optimization_prompt(symbol, results, strategy_name, extended_data)

    # Try primary AI
    if default_ai == 'gemini' and self.gemini_model:
        try:
            response = self.gemini_model.generate_content(prompt)
            result = self._parse_ai_response(response.text)
            if result:
                return result
        except Exception as e:
            logger.error(f"Gemini optimization failed: {e}")
    
    elif default_ai == 'groq' and self.groq_client:
        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-8b-8192",
                temperature=0.7
            )
            response_text = chat_completion.choices[0].message.content
            result = self._parse_ai_response(response_text)
            if result:
                return result
        except Exception as e:
            logger.error(f"Groq optimization failed: {e}")
    
    elif default_ai == 'grok' and GROK_AVAILABLE and self.api_key:
        try:
            result = ask_grok_json(prompt, role="user", model=os.getenv("GROK_MODEL", "grok-4"))
            if result:
                return result
        except Exception as e:
            logger.error(f"Grok optimization failed: {e}")
    
    logger.warning(f"All AI optimization attempts failed for {strategy_name}")
    return None

def _parse_ai_response(self, response_text):
    """Parse AI response, handling markdown code blocks"""
    try:
        # Remove markdown code blocks
        cleaned = response_text.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        if cleaned.startswith('```'):
            cleaned = cleaned[3:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        
        return json.loads(cleaned.strip())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        logger.debug(f"Response text: {response_text[:500]}")
        return None

def _build_optimization_prompt(self, symbol, results, strategy_name, extended_data):
    """Build AI optimization prompt"""
    data_desc = f"using {len(extended_data)} rows of extended data" if extended_data is not None else "using existing data"
    
    prompt_parts = [
        f"Optimize the {strategy_name} strategy for {symbol} ({data_desc}).",
        f"",
        f"Backtest results:",
        f"{json.dumps(results, ensure_ascii=False, indent=2)}",
        f"",
        f"Requirements:",
        f"- Focus on {strategy_name}-specific parameters",
        f"- Maximize expected return while keeping max drawdown < {config.get('strategy_params', {}).get('max_drawdown_threshold', 0.2)}",
        f"- Provide confidence score (0-1)",
        f"",
        f"Output ONLY valid JSON in this exact format:",
        '{',
        f'  "symbol": "{symbol}",',
        f'  "analysis_date": "{datetime.today().strftime("%Y-%m-%d")}",',
        f'  "winning_strategy": {{',
        f'    "name": "{strategy_name}",',
        f'    "confidence": 0.85,',
        f'    "expected_return": 0.15,',
        f'    "max_drawdown": 0.12,',
        f'    "sharpe_ratio": 1.5',
        f'  }},',
        f'  "signals": {{',
        f'    "position": "LONG",',
        f'    "entry_price": 100.0,',
        f'    "target_price": 110.0,',
        f'    "stop_loss": 95.0,',
        f'    "position_size": 0.1',
        f'  }},',
        f'  "dynamic_params": {{}},',
        f'  "strategy_version": "2.0"',
        f'}}'
    ]
    return '\n'.join(prompt_parts)

def optimize_with_grok(self, symbol, results, timeframe, best_results, index_symbol):
    """Grok optimization via HTTP helper"""
    if not GROK_AVAILABLE or not ask_grok_json:
        logger.warning("Grok unavailable, cannot optimize")
        return None
    
    prompt_lines = [
        f"Select the best strategy for {symbol} (timeframe: {timeframe}, index: {index_symbol}).",
        f"",
        f"Backtest results:",
        f"{json.dumps(results, ensure_ascii=False, indent=2)}",
        f"",
        f"Best parameters:",
        f"{json.dumps(best_results, ensure_ascii=False, indent=2)}",
        f"",
        "Requirements:",
        f"- Select strategy with highest expected return",
        f"- Ensure max drawdown < {config.get('strategy_params', {}).get('max_drawdown_threshold', 0.2)}",
        f"- Provide confidence, signals, and dynamic parameters",
        f"",
        "Output ONLY valid JSON:",
        '{',
        f'  "symbol": "{symbol}",',
        f'  "analysis_date": "{datetime.today().strftime("%Y-%m-%d")}",',
        f'  "index_symbol": "{index_symbol}",',
        '  "winning_strategy": {',
        '    "name": "strategy_name",',
        '    "confidence": 0.85,',
        '    "expected_return": 0.15,',
        '    "max_drawdown": 0.12,',
        '    "sharpe_ratio": 1.5',
        '  },',
        '  "signals": {',
        '    "position": "LONG",',
        '    "entry_price": 100.0,',
        '    "target_price": 110.0,',
        '    "stop_loss": 95.0,',
        '    "position_size": 0.1',
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
        logger.error(f"Grok API call failed: {e}")
        return None

def _apply_dynamic_strategy(self, symbol, strategy, timeframe):
    """Apply dynamic strategy (placeholder implementation)"""
    logger.info(f"Applying dynamic strategy for {symbol}")
    return {
        'sharpe_ratio': 0,
        'max_drawdown': 0,
        'expected_return': 0,
        'signals': {
            'position': 'NEUTRAL',
            'entry_price': 0,
            'target_price': 0,
            'stop_loss': 0,
            'position_size': 0
        }
    }
```