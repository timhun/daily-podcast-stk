import os
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

import pandas as pd
import numpy as np
import requests
from backtrader import Cerebro, Strategy, feeds
import backtrader.indicators as btind
from sklearn.ensemble import RandomForestClassifier
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

# === 設定目錄 ===
LOG_DIR = "logs"
DATA_DIR = "data"
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# === Logger ===
logger = logging.getLogger("strategy_manager")
logger.setLevel(logging.INFO)
fh = RotatingFileHandler(
    os.path.join(LOG_DIR, "strategy_manager.log"),
    maxBytes=2_000_000,
    backupCount=3,
    encoding="utf-8"
)
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(fh)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(sh)

# === Grok API 設定 ===
GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_API_URL = os.getenv('GROK_API_URL')

# === 工具函式 ===
def load_config():
    config_file = 'config.json'
    if not os.path.exists(config_file):
        logger.error(f"缺少配置檔案: {config_file}")
        raise FileNotFoundError(f"缺少配置檔案: {config_file}")
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('symbols', []), config.get('strategies', {})
    except json.JSONDecodeError as e:
        logger.error(f"配置檔案解析失敗: {e}")
        raise ValueError(f"配置檔案解析失敗: {e}")

# === 策略類別 ===
class VolumeBreakout(Strategy):
    params = (('volume_multiplier', 1.5),)

    def __init__(self):
        self.volume_ma = btind.SimpleMovingAverage(self.data.volume, period=5)
        self.close_ma = btind.SimpleMovingAverage(self.data.close, period=5)

    def next(self):
        if self.data.volume[0] > self.volume_ma[0] * self.params.volume_multiplier and \
           self.data.close[0] > self.close_ma[0]:
            self.buy()
        elif self.data.close[0] < self.close_ma[0] * 0.98 or \
             self.data.close[0] > self.close_ma[0] * 1.02:
            self.sell()

class MLStrategy(Strategy):
    def __init__(self):
        pass  # 需整合 ML 模型預測

# === ML 模型 ===
def prepare_ml_data(df):
    df['Return'] = df['Close'].pct_change().shift(-1)
    df['Target'] = (df['Return'] > 0).astype(int)
    features = ['Open', 'High', 'Low', 'Close', 'Volume']
    return df.dropna()[features], df.dropna()['Target']

def train_ml_models(df):
    X, y = prepare_ml_data(df)
    # Random Forest
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X, y)
    # LSTM
    model = Sequential()
    model.add(LSTM(50, return_sequences=True, input_shape=(X.shape[1],1)))
    model.add(LSTM(50))
    model.add(Dense(1, activation='sigmoid'))
    model.compile(optimizer='adam', loss='binary_crossentropy')
    X_lstm = np.reshape(X.values, (X.shape[0], X.shape[1], 1))
    model.fit(X_lstm, y.values, epochs=10, batch_size=32, verbose=0)
    return {'rf': rf, 'lstm': model}

# === 回測與基準 ===
def evaluate_strategy(cerebro, data):
    cerebro.adddata(data)
    cerebro.run()
    # 簡化回報計算
    try:
        ret = cerebro.broker.getvalue() / cerebro.broker.startingcash - 1
    except Exception:
        ret = 0
    return ret

def get_market_baseline(df):
    daily_change = df['Close'].pct_change().iloc[-1] * 100
    weekly_change = df['Close'].pct_change(periods=5).iloc[-1] * 100
    return max(daily_change, weekly_change / 5)

def improve_with_grok(current_params):
    if not GROK_API_KEY or not GROK_API_URL:
        logger.warning("缺少 Grok API 設定，跳過改進")
        return current_params
    try:
        response = requests.post(
            GROK_API_URL,
            json={'params': current_params},
            headers={'Authorization': f'Bearer {GROK_API_KEY}'},
            timeout=5
        )
        response.raise_for_status()
        improved_params = response.json().get('improved_params', current_params)
        logger.info(f"Grok API 改進參數: {improved_params}")
        return improved_params
    except Exception as e:
        logger.error(f"Grok API 請求失敗: {e}")
        return current_params

# === 主函式 ===
def main():
    symbols, strategies = load_config()

    for symbol in symbols:
        daily_path = os.path.join(DATA_DIR, f'daily_{symbol}.csv')
        if not os.path.exists(daily_path):
            logger.warning(f"缺少 {daily_path}，跳過 {symbol}")
            continue

        df = pd.read_csv(daily_path)
        df['Date'] = pd.to_datetime(df['Date'])
        baseline_return = get_market_baseline(df)

        best_strategy = None
        best_return = -float('inf')
        best_params = {}

        for strategy_name, params in strategies.items():
            cerebro = Cerebro()
            if strategy_name == 'VolumeBreakout':
                cerebro.addstrategy(VolumeBreakout, **params)
            elif strategy_name == 'MLStrategy':
                ml_models = train_ml_models(df)
                cerebro.addstrategy(MLStrategy)

            data_feed = feeds.PandasData(dataname=df)
            return_value = evaluate_strategy(cerebro, data_feed)

            if return_value > baseline_return and return_value > best_return:
                best_return = return_value
                best_strategy = strategy_name
                best_params = params

        if best_strategy:
            improved_params = improve_with_grok(best_params)
            output = {
                'symbol': symbol,
                'best_strategy': best_strategy,
                'params': improved_params,
                'return': best_return,
                'baseline': baseline_return
            }
            output_path = os.path.join(DATA_DIR, f'strategy_best_{symbol}.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            logger.info(f"為 {symbol} 選出最佳策略: {best_strategy}, 回報率: {best_return:.2f}%, 基準: {baseline_return:.2f}%")
        else:
            logger.warning(f"{symbol} 無勝過基準的策略")

if __name__ == '__main__':
    logger.info("策略管理師開始執行")
    try:
        main()
    except Exception as e:
        logger.exception(f"策略管理師執行失敗: {e}")
    logger.info("策略管理師執行結束")