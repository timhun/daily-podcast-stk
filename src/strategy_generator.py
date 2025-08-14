# src/strategy_generator.py
import os, textwrap
import pandas as pd

def make_weekly_report(df: pd.DataFrame):
    vol20 = float(df["ret"].rolling(20).std().iloc[-1])
    vol60 = float(df["ret"].rolling(60).std().iloc[-1])
    trend = float((df["ma20"].iloc[-1] - df["ma60"].iloc[-1]) / df["ma60"].iloc[-1])
    regime = "trend" if (trend > 0 and vol20 <= vol60) else "range"
    return {
        "asof": str(df.index[-1]),
        "stats": {"vol20": vol20, "vol60": vol60, "trend_ma20_ma60": trend},
        "regime_hint": regime
    }

def generate_strategy_file(weekly_report: dict, out_path="strategy_candidate.py"):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    regime = weekly_report.get("regime_hint", "trend")

    if regime == "trend":
        code = r'''
import pandas as pd, numpy as np
class StrategyCandidate:
    """Trend strategy: MA(20/60) + RSI filter"""
    params = dict(fast=20, slow=60, rsi_n=14, rsi_lo=35, rsi_hi=75,
                  size_pct=0.6, stop_loss=0.08)

    @staticmethod
    def _rsi(series, n=14):
        delta = series.diff()
        up = delta.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
        dn = -delta.clip(upper=0).ewm(alpha=1/n, adjust=False).mean()
        rs = up/dn.replace(0, np.nan)
        return 100 - (100/(1+rs))

    @staticmethod
    def generate_signal(df: pd.DataFrame):
        px = df['close']
        ma_f = px.rolling(StrategyCandidate.params['fast']).mean()
        ma_s = px.rolling(StrategyCandidate.params['slow']).mean()
        rsi = StrategyCandidate._rsi(px, StrategyCandidate.params['rsi_n'])
        cross_up = (ma_f.iloc[-2] <= ma_s.iloc[-2]) and (ma_f.iloc[-1] > ma_s.iloc[-1])
        cross_dn = (ma_f.iloc[-2] >= ma_s.iloc[-2]) and (ma_f.iloc[-1] < ma_s.iloc[-1])
        if cross_up and rsi.iloc[-1] > 50:
            return {"signal":"buy", "size_pct": StrategyCandidate.params['size_pct']}
        if cross_dn or rsi.iloc[-1] > StrategyCandidate.params['rsi_hi']:
            return {"signal":"sell", "size_pct": StrategyCandidate.params['size_pct']}
        return {"signal":"hold"}
'''
    else:
        code = r'''
import pandas as pd, numpy as np
class StrategyCandidate:
    """Range strategy: BBands + RSI"""
    params = dict(n=20, k=2.0, rsi_n=14, rsi_lo=30, rsi_hi=70,
                  size_pct=0.5, stop_loss=0.07)

    @staticmethod
    def _rsi(series, n=14):
        delta = series.diff()
        up = delta.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
        dn = -delta.clip(upper=0).ewm(alpha=1/n, adjust=False).mean()
        rs = up/dn.replace(0, np.nan)
        return 100 - (100/(1+rs))

    @staticmethod
    def generate_signal(df: pd.DataFrame):
        px = df['close']
        mid = px.rolling(StrategyCandidate.params['n']).mean()
        std = px.rolling(StrategyCandidate.params['n']).std()
        up  = mid + StrategyCandidate.params['k']*std
        dn  = mid - StrategyCandidate.params['k']*std
        rsi = StrategyCandidate._rsi(px, StrategyCandidate.params['rsi_n'])
        touch_dn = px.iloc[-1] < dn.iloc[-1]
        touch_up = px.iloc[-1] > up.iloc[-1]
        if touch_dn and rsi.iloc[-1] < StrategyCandidate.params['rsi_lo']:
            return {"signal":"buy", "size_pct": StrategyCandidate.params['size_pct']}
        if touch_up and rsi.iloc[-1] > StrategyCandidate.params['rsi_hi']:
            return {"signal":"sell", "size_pct": StrategyCandidate.params['size_pct']}
        return {"signal":"hold"}
'''
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(code).lstrip())
    return out_path