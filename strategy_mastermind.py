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
import yfinance as yf  # 新增，用於載入更多數據
from threading import Thread  # 新增，背景運行優化

# 條件導入 AI 庫（避免 ModuleNotFoundError）
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

# 計算移動平均線
def calculate_ma(prices, window):
    if not isinstance(prices, pd.Series):
        raise ValueError(f"prices 必須是 pandas.Series，收到 {type(prices)}")
    return prices.rolling(window=window).mean()

# 判斷三線多頭
def is_bullish(ma_short, ma_mid, ma_long):
    return (ma_short > ma_mid) & (ma_mid > ma_long)

# 計算強化指數
def composite_index_with_weights(prices, volume, weight_stock_info, weights=[0.4, 0.35, 0.25]):
    if not isinstance(prices, pd.Series) or not isinstance(volume, pd.Series):
        raise ValueError(f"prices 和 volume 必須是 pandas.Series，收到 prices: {type(prices)}, volume: {type(volume)}")
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
        self.ai_config = config.get('ai_optimizer', {'default_ai': 'grok'})  # 確保有 fallback
        self.gemini_model = None
        self.groq_client = None
        self._load_strategies()
        self._init_ai_clients()

    def _load_strategies(self):
        """載入策略，優先使用優化 params"""
        strategy_classes = {
            'technical': TechnicalStrategy,
            'ml': MLStrategy,
            'bigline': BigLineStrategy
        }
        for name, strategy_class in strategy_classes.items():
            # 優先載入優化 params
            optimized_path = f"{config['data_paths']['strategy']}/{name}_optimized.json"
            params = self._load_json_params(optimized_path) or self._load_default_params(name)
            strategy = strategy_class(config, params)
            self.models[name] = strategy
            logger.info(f"{name} 策略載入完成 (優化 params: {os.path.exists(optimized_path)})")

    def _load_default_params(self, name):
        """載入預設 params"""
        try:
            with open(f'strategies/{name}_strategy.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error(f"Failed to load {name}_strategy.json, using default params")
            return {}  # 子類會處理預設

    def _load_json_params(self, path):
        """載入 JSON params"""
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in {path}: {e}")
        return None

    def _init_ai_clients(self):
        """初始化 AI 客戶端，帶 fallback"""
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
        """原有方法：基本回測，不變"""
        # ... 您的原有 run_strategy_tournament 邏輯（從提供的內容推斷，假設完整）...
        # 這裡省略，保留原樣，包括 get_param_combinations、backtest 循環、optimize_with_grok 等
        # 優化調用移到外部（main.py）

    def optimize_all_strategies(self, strategy_results, mode, iterations=1, extended_data=False, background=True):
        """獨立優化每個策略，可背景運行"""
        def _optimize_thread():
            data_period = config['ai_optimizer']['optimization']['weekend_data_period'] if extended_data else config['ai_optimizer']['optimization']['weekday_data_period']
            symbol = list(strategy_results.keys())[0]  # 使用第一個 symbol
            extended_df = self._load_extended_data(symbol, data_period)
            for name, strategy in self.models.items():
                logger.info(f"優化 {name} 策略 (迭代 {iterations} 次)...")
                for i in range(iterations):
                    optimized = self.optimize_with_ai(strategy_results[name], name, extended_df)
                    if optimized:
                        # 更新 params
                        strategy.params.update(optimized.get('dynamic_params', {}))
                        self._save_optimized_params(name, strategy.params)
                        logger.info(f"{name} 第 {i+1} 次優化完成: {optimized['winning_strategy']}")

        if background:
            thread = Thread(target=_optimize_thread)
            thread.daemon = True
            thread.start()
            logger.info("優化在背景執行中...")
        else:
            _optimize_thread()

    def _load_extended_data(self, symbol, period):
        """載入更多歷史數據，快取到 CSV"""
        cache_path = f"{config['data_paths']['market']}/extended_{symbol.replace('^', '').replace('.', '_')}.csv"
        if os.path.exists(cache_path):
            df = pd.read_csv(cache_path)
            df['date'] = pd.to_datetime(df['date'])
            logger.info(f"載入快取擴展數據: {len(df)} 筆")
            return df
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        if hist.empty:
            logger.warning(f"{symbol} 擴展數據載入失敗，使用現有數據")
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
        logger.info(f"擴展數據載入並快取: {len(df)} 筆")
        return df

    def _save_optimized_params(self, strategy_name, params):
        """儲存優化 params"""
        path = f"{config['data_paths']['strategy']}/{strategy_name}_optimized.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(params, f, ensure_ascii=False, indent=2)
        logger.info(f"{strategy_name} 優化 params 儲存至: {path}")

    def optimize_with_ai(self, results, strategy_name, extended_data=None):
        """通用 AI 優化，支援 Grok/Gemini/Groq，fallback 到 Grok"""
        default_ai = self.ai_config.get('default_ai', 'grok')
        prompt = self._build_optimization_prompt(results, strategy_name, extended_data)

        if default_ai == 'grok':
            return self.optimize_with_grok(prompt)
        elif default_ai == 'gemini' and self.gemini_model:
            try:
                response = self.gemini_model.generate_content(prompt)
                return json.loads(response.text.strip('```json\n').strip('```\n'))
            except Exception as e:
                logger.error(f"Gemini 優化失敗: {e}")
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
                logger.error(f"Groq 優化失敗: {e}")
                return self.optimize_with_grok(prompt)
        else:
            logger.warning(f"No valid AI for {default_ai}, falling back to Grok")
            return self.optimize_with_grok(prompt)

    def _build_optimization_prompt(self, results, strategy_name, extended_data):
        """建構 AI 提示"""
        data_desc = f"使用 {len(extended_data)} 筆擴展數據" if extended_data is not None else "使用現有數據"
        return f"""
        為 {strategy_name} 策略優化（{data_desc}）。回測結果：{json.dumps(results, ensure_ascii=False, indent=2)}
        要求：選擇預期報酬最高的策略，且最大回撤 < {config['strategy_params']['max_drawdown_threshold']}。聚焦 {strategy_name} 特定指標（如 RSI 閾值）。
        提供最佳策略名稱、信心分數、預期報酬、最大回撤、夏普比率、交易信號和動態參數。
        格式為 JSON：
        ```json
        {{
          "symbol": "symbol",
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
          }},
          "dynamic_params": {{}},
          "strategy_version": "2.0"
        }}
