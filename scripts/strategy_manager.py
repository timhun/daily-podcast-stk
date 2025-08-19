# scripts/strategy_manager.py
import os
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

import pandas as pd
import numpy as np
import requests

import backtrader as bt
from backtrader import Cerebro, Strategy, feeds
import backtrader.indicators as btind

from sklearn.ensemble import RandomForestClassifier

# ===== 可選用 LSTM（預設關閉以加速 CI） =====
ENABLE_LSTM = os.getenv("ENABLE_LSTM", "0") == "1"
if ENABLE_LSTM:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense

# === 目錄 ===
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
GROK_API_URL = os.getenv('GROK_API_URL')  # 可留空，會自動跳過

# === 讀設定 ===
def load_config():
    cfg_path = "config.json"
    if not os.path.exists(cfg_path):
        raise FileNotFoundError("缺少 config.json")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    symbols = cfg.get("symbols", [])
    strategies = cfg.get("strategies", {
        "VolumeBreakout": {"volume_multiplier": 1.5},
        "MLStrategy": {"model": "rf"}
    })
    benchmark_map = cfg.get("benchmark_map", {})  # e.g. {"0050.TW":"^TWII","QQQ":"^IXIC"}
    return symbols, strategies, benchmark_map

# === 讀檔並確保數值欄位 ===
NUM_COLS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]

def load_daily_csv(symbol):
    path = os.path.join(DATA_DIR, f"daily_{symbol}.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    if "Date" not in df.columns:
        return None
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for c in NUM_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["Date", "Open", "High", "Low", "Close", "Volume"]).copy()
    df = df.sort_values("Date")
    return df

# === Baseline（從對應大盤算；沒有就用自己） ===
def compute_baseline_return(symbol, df_symbol, benchmark_map):
    bench_symbol = benchmark_map.get(symbol, symbol)
    df_bench = load_daily_csv(bench_symbol)
    if df_bench is None or df_bench.empty:
        df_bench = df_symbol
    # 使用最近 60 根（日K）平均日報酬作為 baseline（%）
    dfb = df_bench.tail(60).copy()
    if len(dfb) < 3:
        return 0.0
    daily_ret = dfb["Close"].pct_change()
    baseline = float(np.nanmean(daily_ret)) * 100.0
    return baseline

# === 策略 ===
class VolumeBreakout(Strategy):
    params = (('volume_multiplier', 1.5),)

    def __init__(self):
        self.volume_ma = btind.SMA(self.data.volume, period=5)
        self.close_ma = btind.SMA(self.data.close, period=5)

    def next(self):
        if self.position.size == 0:
            if self.data.volume[0] > self.volume_ma[0] * self.p.volume_multiplier and \
               self.data.close[0] > self.close_ma[0]:
                self.buy()
        else:
            # 簡單移動停利/停損
            if self.data.close[0] < self.close_ma[0] * 0.98 or \
               self.data.close[0] > self.close_ma[0] * 1.02:
                self.sell()

class MLStrategy(Strategy):
    params = (('rf', None), ('lstm', None), ('use', 'rf'))

    def __init__(self):
        self.window = 1  # 這裡做 T+1 方向預測
        self.buffer = []

    def next(self):
        o = float(self.data.open[0])
        h = float(self.data.high[0])
        l = float(self.data.low[0])
        c = float(self.data.close[0])
        v = float(self.data.volume[0])

        # RandomForest：用當根價格量能特徵做隔日上漲機率判斷
        pred_up = 0.5
        if self.p.use == "rf" and self.p.rf is not None:
            try:
                pred_up = float(self.p.rf.predict([[o, h, l, c, v]])[0])
            except Exception:
                pred_up = 0.5
        elif self.p.use == "lstm" and self.p.lstm is not None and ENABLE_LSTM:
            # 簡化處理：單步 features -> (timesteps=5, features=1) 需自行緩衝過去值
            self.buffer.append([o, h, l, c, v])
            if len(self.buffer) >= 5:
                arr = np.array(self.buffer[-5:], dtype=float).mean(axis=1).reshape(5, 1)  # 很保守的簡化
                arr = arr.reshape(1, 5, 1)
                p = float(self.p.lstm.predict(arr, verbose=0)[0][0])
                pred_up = p

        # 簡單決策：>0.5 做多，否則清倉
        if pred_up > 0.5 and self.position.size == 0:
            self.buy()
        elif pred_up <= 0.5 and self.position.size != 0:
            self.close()

# === ML 資料/訓練 ===
def prepare_ml_data(df):
    df = df.copy()
    df["Return"] = df["Close"].pct_change().shift(-1)
    df["Target"] = (df["Return"] > 0).astype(int)
    feats = ["Open", "High", "Low", "Close", "Volume"]
    ds = df.dropna(subset=feats + ["Target"])
    X = ds[feats].values
    y = ds["Target"].values
    return X, y

def train_models(df):
    X, y = prepare_ml_data(df)
    if len(X) < 100:
        # 數據太短，給個簡單 RF
        rf = RandomForestClassifier(n_estimators=50, random_state=42).fit(X, y)
        models = {"rf": rf, "lstm": None}
        return models

    rf = RandomForestClassifier(n_estimators=150, max_depth=None, random_state=42)
    rf.fit(X, y)

    lstm_model = None
    if ENABLE_LSTM:
        # 把特徵粗暴 reshape 成 (samples, timesteps, features=1)
        X_lstm = X.reshape(X.shape[0], X.shape[1], 1)
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense
        lstm_model = Sequential()
        lstm_model.add(LSTM(32, return_sequences=True, input_shape=(X_lstm.shape[1], 1)))
        lstm_model.add(LSTM(32))
        lstm_model.add(Dense(1, activation='sigmoid'))
        lstm_model.compile(optimizer='adam', loss='binary_crossentropy')
        lstm_model.fit(X_lstm, y, epochs=5, batch_size=64, verbose=0)

    models = {"rf": rf, "lstm": lstm_model}
    return models

# === 回測與績效 ===
def make_bt_feed(df):
    df_bt = df.copy()
    df_bt = df_bt.set_index("Date")
    # Backtrader 預設欄位: Open/High/Low/Close/Volume/OpenInterest
    if "OpenInterest" not in df_bt.columns:
        df_bt["OpenInterest"] = 0
    return feeds.PandasData(dataname=df_bt)

def run_backtest(strategy_cls, params, df):
    cerebro = Cerebro()
    cerebro.broker.setcash(100_000.0)
    cerebro.broker.setcommission(commission=0.001)  # 0.1% 交易成本
    cerebro.addsizer(bt.sizers.FixedSize, stake=10)

    data_feed = make_bt_feed(df)
    cerebro.adddata(data_feed)
    cerebro.addstrategy(strategy_cls, **params)

    start_value = cerebro.broker.getvalue()
    cerebro.run()
    end_value = cerebro.broker.getvalue()
    ret = (end_value - start_value) / start_value * 100.0  # %
    return float(ret)

# === Grok API ===
def improve_with_grok(payload):
    if not GROK_API_KEY or not GROK_API_URL:
        return payload.get("params", {})
    try:
        r = requests.post(
            GROK_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {GROK_API_KEY}"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("improved_params", payload.get("params", {}))
    except Exception as e:
        logger.warning(f"Grok API 失敗：{e}")
        return payload.get("params", {})

# === 主流程 ===
def main():
    symbols, strategies, benchmark_map = load_config()

    for symbol in symbols:
        df = load_daily_csv(symbol)
        if df is None or df.empty:
            logger.warning(f"缺少或無效資料：data/daily_{symbol}.csv，跳過")
            continue

        baseline = compute_baseline_return(symbol, df, benchmark_map)
        logger.info(f"[{symbol}] Baseline(日均 %) = {baseline:.4f}")

        best_name, best_params, best_return = None, None, -1e9

        # 預先訓練 ML（避免每次 strategy 重訓）
        models = None
        if "MLStrategy" in strategies:
            try:
                models = train_models(df)
            except Exception as e:
                logger.warning(f"[{symbol}] 訓練 ML 失敗：{e}")
                models = {"rf": None, "lstm": None}

        for strat_name, params in strategies.items():
            try:
                if strat_name == "VolumeBreakout":
                    ret = run_backtest(VolumeBreakout, params, df)
                elif strat_name == "MLStrategy":
                    use_model = params.get("model", "rf")
                    rf = models["rf"] if models else None
                    lstm_m = models["lstm"] if models else None
                    ret = run_backtest(MLStrategy, {"rf": rf, "lstm": lstm_m, "use": use_model}, df)
                else:
                    logger.info(f"未知策略 {strat_name}，跳過")
                    continue
            except Exception as e:
                logger.warning(f"[{symbol}] 策略 {strat_name} 回測失敗：{e}")
                continue

            logger.info(f"[{symbol}] 策略 {strat_name} 回測報酬：{ret:.2f}%（Baseline {baseline:.2f}%）")
            if ret > 0 and ret > baseline and ret > best_return:
                best_name, best_params, best_return = strat_name, params, ret

        if best_name:
            # 送 Grok 調參
            improved = improve_with_grok({
                "symbol": symbol,
                "strategy": best_name,
                "params": best_params,
                "metrics": {"return_pct": best_return, "baseline_pct": baseline}
            })

            out = {
                "symbol": symbol,
                "best_strategy": best_name,
                "params": improved,
                "return_pct": round(best_return, 4),
                "baseline_pct": round(baseline, 4),
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            }
            out_path = os.path.join(DATA_DIR, f"strategy_best_{symbol}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
            logger.info(f"[{symbol}] ✅ 最佳策略：{best_name} | Return {best_return:.2f}% > Baseline {baseline:.2f}% → 已輸出 {out_path}")
        else:
            logger.info(f"[{symbol}] 無策略勝過 Baseline（或正報酬）")

if __name__ == "__main__":
    logger.info("策略管理師開始執行")
    try:
        main()
    except Exception as e:
        logger.exception(f"策略管理師執行失敗: {e}")
    logger.info("策略管理師執行結束")