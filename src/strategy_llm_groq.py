#!/usr/bin/env python3
# src/strategy_llm_groq.py
import os, json
from datetime import date

def generate_strategy(df, history=None):
    """
    使用 LLM/Groq 生成策略 JSON
    history: dict, 歷史策略績效
    """
    # --- 簡單例子：Trend 或 Range
    vol20 = float(df["ret"].rolling(20).std().iloc[-1])
    vol60 = float(df["ret"].rolling(60).std().iloc[-1])
    trend = float((df["ma20"].iloc[-1] - df["ma60"].iloc[-1]) / df["ma60"].iloc[-1])
    regime = "trend" if (trend > 0 and vol20 <= vol60) else "range"

    strategy_data = {
        "asof": str(df.index[-1]),
        "regime": regime,
        "params": {},
        "description": "",
        "history": history or {}
    }

    if regime == "trend":
        strategy_data["params"] = {"fast":20, "slow":60, "rsi_n":14, "rsi_lo":35, "rsi_hi":75, "size_pct":0.6, "stop_loss":0.08}
        strategy_data["description"] = "Trend strategy: MA(20/60) + RSI filter"
    else:
        strategy_data["params"] = {"n":20, "k":2.0, "rsi_n":14, "rsi_lo":30, "rsi_hi":70, "size_pct":0.5, "stop_loss":0.07}
        strategy_data["description"] = "Range strategy: BBands + RSI"

    return strategy_data
