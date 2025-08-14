# src/strategy_default.py
import pandas as pd, numpy as np

class StrategyCandidate:
    """
    Default safe strategy (保底)：
    - 簡單均線交叉 MA5 / MA20，size_pct 小，保守止損
    用途：如果沒有 weekly 生成的策略，daily job 可使用此策略避免失敗
    """
    params = dict(fast=5, slow=20, size_pct=0.2, stop_loss=0.06)

    @staticmethod
    def generate_signal(df: pd.DataFrame):
        px = df['close']
        if len(px) < StrategyCandidate.params['slow'] + 2:
            return {"signal": "hold", "size_pct": 0.0}
        ma_f = px.rolling(StrategyCandidate.params['fast']).mean()
        ma_s = px.rolling(StrategyCandidate.params['slow']).mean()
        cross_up = (ma_f.iloc[-2] <= ma_s.iloc[-2]) and (ma_f.iloc[-1] > ma_s.iloc[-1])
        cross_dn = (ma_f.iloc[-2] >= ma_s.iloc[-2]) and (ma_f.iloc[-1] < ma_s.iloc[-1])
        if cross_up:
            return {"signal": "buy", "size_pct": StrategyCandidate.params['size_pct']}
        if cross_dn:
            return {"signal": "sell", "size_pct": StrategyCandidate.params['size_pct']}
        return {"signal":"hold", "size_pct": 0.0}