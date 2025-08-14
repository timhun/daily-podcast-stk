#!/usr/bin/env python3
# src/strategy_llm_groq.py
import datetime, json
import pandas as pd
import numpy as np

def generate_strategy_llm(df: pd.DataFrame, history: dict):
    """
    透過 LLM/Groq 生成策略 JSON
    df: OHLCV DataFrame
    history: 之前策略結果
    return: strategy_data dict
    """
    # 取得最新 20/60 MA、波動率
    px = df['close']
    ma20 = px.rolling(20).mean().iloc[-1]
    ma60 = px.rolling(60).mean().iloc[-1]
    vol20 = px.pct_change().rolling(20).std().iloc[-1]
    vol60 = px.pct_change().rolling(60).std().iloc[-1]

    # 判斷市場型態
    trend = (ma20 - ma60)/ma60
    regime = "trend" if trend > 0 and vol20 <= vol60 else "range"

    # LLM/Groq 模擬生成策略參數（實際可接 Groq API）
    if regime == "trend":
        params = dict(fast=20, slow=60, rsi_n=14, rsi_lo=35, rsi_hi=75,
                      size_pct=0.6, stop_loss=0.08)
    else:
        params = dict(n=20, k=2.0, rsi_n=14, rsi_lo=30, rsi_hi=70,
                      size_pct=0.5, stop_loss=0.07)

    # 可以把歷史績效作為策略微調依據
    last_perf = history.get("history", [])[-1] if history.get("history") else {}
    strategy_data = {
        "date": str(datetime.date.today()),
        "regime": regime,
        "params": params,
        "history_reference": last_perf
    }
    return strategy_data
