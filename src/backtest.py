import pandas as pd
import numpy as np

def run_backtest(df, strategy_data, cash=1_000_000, commission=0.001):
    """
    支援 JSON strategy_data
    return: metrics dict
    """
    # 簡單示意：用 MA(20/60) 趨勢判斷模擬回測績效
    px = df['close']
    if strategy_data["regime"] == "trend":
        ma_f = px.rolling(strategy_data["params"]["fast"]).mean()
        ma_s = px.rolling(strategy_data["params"]["slow"]).mean()
        positions = (ma_f > ma_s).astype(int)
    else:
        mid = px.rolling(strategy_data["params"]["n"]).mean()
        std = px.rolling(strategy_data["params"]["n"]).std()
        up = mid + strategy_data["params"]["k"]*std
        dn = mid - strategy_data["params"]["k"]*std
        positions = ((px < dn).astype(int) - (px > up).astype(int))

    ret = px.pct_change().fillna(0) * positions.shift(1).fillna(0)
    portfolio = (1 + ret).cumprod() * cash
    total_return = portfolio.iloc[-1]/cash - 1
    annual_return = total_return / (len(df)/252)
    max_drawdown = (portfolio.cummax() - portfolio).max() / portfolio.cummax().max()
    sharpe_ratio = (annual_return - 0.02) / (ret.std() * np.sqrt(252))

    return {
        "in_sample_final_value": portfolio.iloc[-1],
        "out_sample_final_value": portfolio.iloc[-1],
        "total_return": total_return,
        "annual_return": annual_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio
    }
