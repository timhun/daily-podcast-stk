#!/usr/bin/env python3
# src/strategy_llm_groq.py
import pandas as pd
import numpy as np
from datetime import datetime

def make_weekly_report(df: pd.DataFrame):
    """生成週報，提供 regime hint"""
    vol20 = float(df["ret"].rolling(20).std().iloc[-1])
    vol60 = float(df["ret"].rolling(60).std().iloc[-1])
    trend = float((df["ma20"].iloc[-1] - df["ma60"].iloc[-1]) / df["ma60"].iloc[-1])
    regime = "trend" if (trend > 0 and vol20 <= vol60) else "range"
    return {
        "asof": str(df.index[-1]),
        "stats": {"vol20": vol20, "vol60": vol60, "trend_ma20_ma60": trend},
        "regime_hint": regime
    }

def generate_strategy_json(weekly_report: dict):
    """生成標準化 strategy_data JSON"""
    regime = weekly_report.get("regime_hint", "trend")
    strategy = {"name": "", "summary": "", "params": {}, "generate_signal": None}

    if regime == "trend":
        strategy["name"] = "Trend Strategy"
        strategy["summary"] = "使用 MA(20/60) 交叉 + RSI 濾網的趨勢追蹤策略"
        strategy["params"] = dict(fast=20, slow=60, rsi_n=14, rsi_lo=35, rsi_hi=75,
                                  size_pct=0.6, stop_loss=0.08)

        def trend_signal(df: pd.DataFrame):
            px = df['close']
            ma_f = px.rolling(strategy["params"]['fast']).mean()
            ma_s = px.rolling(strategy["params"]['slow']).mean()
            delta = px.diff()
            up = delta.clip(lower=0).ewm(alpha=1/strategy["params"]['rsi_n'], adjust=False).mean()
            dn = -delta.clip(upper=0).ewm(alpha=1/strategy["params"]['rsi_n'], adjust=False).mean()
            rs = up / dn.replace(0, np.nan)
            rsi = 100 - (100/(1+rs))
            cross_up = (ma_f.iloc[-2] <= ma_s.iloc[-2]) and (ma_f.iloc[-1] > ma_s.iloc[-1])
            cross_dn = (ma_f.iloc[-2] >= ma_s.iloc[-2]) and (ma_f.iloc[-1] < ma_s.iloc[-1])
            if cross_up and rsi.iloc[-1] > 50:
                return {"signal":"buy", "size_pct": strategy["params"]['size_pct']}
            if cross_dn or rsi.iloc[-1] > strategy["params"]['rsi_hi']:
                return {"signal":"sell", "size_pct": strategy["params"]['size_pct']}
            return {"signal":"hold"}

        strategy["generate_signal"] = trend_signal

    else:
        strategy["name"] = "Range Strategy"
        strategy["summary"] = "使用 BBands + RSI 的盤整區間策略"
        strategy["params"] = dict(n=20, k=2.0, rsi_n=14, rsi_lo=30, rsi_hi=70,
                                  size_pct=0.5, stop_loss=0.07)

        def range_signal(df: pd.DataFrame):
            px = df['close']
            mid = px.rolling(strategy["params"]['n']).mean()
            std = px.rolling(strategy["params"]['n']).std()
            up  = mid + strategy["params"]['k']*std
            dn  = mid - strategy["params"]['k']*std
            delta = px.diff()
            up_rsi = delta.clip(lower=0).ewm(alpha=1/strategy["params"]['rsi_n'], adjust=False).mean()
            dn_rsi = -delta.clip(upper=0).ewm(alpha=1/strategy["params"]['rsi_n'], adjust=False).mean()
            rs = up_rsi / dn_rsi.replace(0, np.nan)
            rsi = 100 - (100/(1+rs))
            touch_dn = px.iloc[-1] < dn.iloc[-1]
            touch_up = px.iloc[-1] > up.iloc[-1]
            if touch_dn and rsi.iloc[-1] < strategy["params"]['rsi_lo']:
                return {"signal":"buy", "size_pct": strategy["params"]['size_pct']}
            if touch_up and rsi.iloc[-1] > strategy["params"]['rsi_hi']:
                return {"signal":"sell", "size_pct": strategy["params"]['size_pct']}
            return {"signal":"hold"}

        strategy["generate_signal"] = range_signal

    return strategy
