import pandas as pd
import json
import os
from datetime import datetime
import logging
from backtrader import Cerebro, Strategy
import backtrader.indicators as btind
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
import requests
import asyncio

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置 Grok API
GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_API_URL = "https://api.grok.xai.com/v1/improve_strategy"

def load_config():
    """載入配置檔案 config.json"""
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

class VolumeBreakout(Strategy):
    """簡單量價突破策略"""
    params = (('volume_multiplier', 1.5),)

    def __init__(self):
        self.volume_ma = btind.SimpleMovingAverage(self.data.volume, period=5)
        self.close_ma = btind.SimpleMovingAverage(self.data.close, period=5)

    def next(self):
        if self.data.volume[0] > self.volume_ma[0] * self.params.volume_multiplier and self.data.close[0] > self.close_ma[0]:
            self.buy()
        elif self.data.close[0] < self.close_ma[0] * 0.98 or self.data.close[0] > self.close_ma[0] * 1.02:
            self.sell()

class MLStrategy(Strategy):
    """基於 ML 的策略"""
    params = (('model_type', 'rf'), ('model', None))

    def __init__(self):
        self.model = self.params.model
        self.features = ['Open', 'High', 'Low', 'Close', 'Volume']

    def next(self):
        X = np.array([self.data.get(size=5)[-1][self.features]]).reshape(1, -1)
        if self.params.model_type == 'rf':
            prediction = self.model.predict(X)[0]
        else:  # LSTM
            X_lstm = X.reshape(1, X.shape[1], 1)
            prediction = self.model.predict(X_lstm)[0][0] > 0.5
        if prediction and not self.position:
            self.buy()
        elif not prediction and self.position:
            self.sell()

def prepare_ml_data(df):
    """準備 ML 數據"""
    df['Return'] = df['Close'].pct_change().shift(-1)
    df['Target'] = (df['Return'] > 0).astype(int)
    features = ['Open', 'High', 'Low', 'Close', 'Volume']
    return df.dropna()[features], df.dropna()['Target']

def train_ml_models(df, symbol):
    """訓練 Random Forest 和 LSTM 模型"""
    X, y = prepare_ml_data(df)
    # Random Forest
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X, y)
    # LSTM
    model = Sequential()
    model.add(LSTM(50, return_sequences=True, input_shape=(X.shape[1], 1)))
    model.add(LSTM(50))
    model.add(Dense(1, activation='sigmoid'))
    model.compile(optimizer='adam', loss='binary_crossentropy')
    X_lstm = np.reshape(X.values, (X.shape[0], X.shape[1], 1))
    model.fit(X_lstm, y.values, epochs=10, batch_size=32, verbose=0)
    return {'rf': rf, 'lstm': model}

def evaluate_strategy(cerebro, symbol, data, strategy, params):
    """評估策略回測結果"""
    cerebro.adddata(data)
    cerebro.addstrategy(strategy, **params)
    cerebro.run()
    return cerebro.broker.getvalue() / cerebro.broker.getvalue() - 1  # 簡化回報率

def get_market_baseline(df):
    """計算大盤每日/每周漲跌幅作為基準"""
    daily_change = df['Close'].pct_change().iloc[-1] * 100
    weekly_change = df['Close'].pct_change(periods=5).iloc[-1] * 100 / 5
    baseline = max(daily_change, weekly_change)
    with open('logs/baseline_history.log', 'a') as f:
        f.write(f"{datetime.now()}: {df['Symbol'].iloc[0]} Baseline: {baseline:.2f}%\n")
    return baseline

async def improve_with_grok(current_params, symbol):
    """使用 Grok API 異步改進策略參數"""
    if not GROK_API_KEY:
        logger.warning(f"缺少 GROK_API_KEY，跳過 {symbol} 改進")
        return current_params
    try:
        response = requests.post(GROK_API_URL, json={'params': current_params, 'symbol': symbol}, headers={'Authorization': f'Bearer {GROK_API_KEY}'})
        response.raise_for_status()
        improved_params = response.json().get('improved_params', current_params)
        logger.info(f"Grok API 改進 {symbol} 參數: {improved_params}")
        return improved_params
    except Exception as e:
        logger.error(f"Grok API 請求 {symbol} 失敗: {e}")
        return current_params

async def main():
    """主函數，執行策略管理"""
    symbols, strategies = load_config()
    data_dir = 'data'

    tasks = []
    for symbol in symbols:
        daily_path = os.path.join(data_dir, f'daily_{symbol}.csv')
        if not os.path.exists(daily_path):
            logger.error(f"缺少 {daily_path}，跳過 {symbol}")
            continue

        df = pd.read_csv(daily_path)
        df['Date'] = pd.to_datetime(df['Date'])
        baseline_return = get_market_baseline(df)

        cerebro = Cerebro()
        best_strategy = None
        best_return = -float('inf')
        best_params = {}

        for strategy_name, params in strategies.items():
            cerebro = Cerebro()
            if strategy_name == 'VolumeBreakout':
                strategy_class = VolumeBreakout
            elif strategy_name == 'MLStrategy':
                ml_models = train_ml_models(df, symbol)
                strategy_class = MLStrategy
                params['model'] = ml_models['rf'] if params.get('model_type', 'rf') == 'rf' else ml_models['lstm']
                params['model_type'] = params.get('model_type', 'rf')

            data = btind.PandasData(dataname=df)
            return_value = evaluate_strategy(cerebro, symbol, data, strategy_class, params)
            if return_value > baseline_return and return_value > 0:
                if return_value > best_return:
                    best_return = return_value
                    best_strategy = strategy_name
                    best_params = params.copy()

        if best_strategy:
            improved_params = await improve_with_grok(best_params, symbol)
            output = {
                'symbol': symbol,
                'best_strategy': best_strategy,
                'params': improved_params,
                'return': best_return,
                'baseline': baseline_return
            }
            output_path = os.path.join(data_dir, f'strategy_best_{symbol}.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            logger.info(f"為 {symbol} 選出最佳策略: {best_strategy}, 回報率: {best_return:.2f}%, 基準: {baseline_return:.2f}%")
        else:
            logger.warning(f"{symbol} 無勝過基準的策略")

if __name__ == '__main__':
    asyncio.run(main())
