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
