import pandas as pd

def run_backtest_json(df, strategy_data, cash=1_000_000):
    """
    回測，直接使用 JSON 格式策略
    """
    df = df.sort_index()
    oos_months = 6
    split_point = df.index[-1] - pd.DateOffset(months=oos_months)
    df_train = df[df.index <= split_point]
    df_test = df[df.index > split_point]

    # 簡單績效計算（示意）
    portfolio_train = cash * (1 + df_train["ret"].mean())
    portfolio_test  = portfolio_train * (1 + df_test["ret"].mean())
    total_return = (portfolio_test - cash) / cash
    annual_return = total_return / (len(df)/252)
    max_drawdown = (df["close"].cummax() - df["close"]).max() / df["close"].cummax().max()
    sharpe_ratio = (annual_return - 0.02) / (df["close"].pct_change().std() * (252 ** 0.5))

    metrics = {
        "in_sample_final_value": portfolio_train,
        "out_sample_final_value": portfolio_test,
        "total_return": total_return,
        "annual_return": annual_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio
    }
    return metrics

def run_daily_sim_json(df, strategy_data, cash=1_000_000):
    """
    每日模擬交易
    """
    last_close = df["close"].iloc[-1]
    # signal: 依 MA/RSI 或 BB 判斷（示意）
    signal = "hold"
    size_pct = strategy_data["params"].get("size_pct", 0.5)
    price = last_close

    if strategy_data["regime"] == "trend":
        ma_f = df["close"].rolling(strategy_data["params"]["fast"]).mean().iloc[-1]
        ma_s = df["close"].rolling(strategy_data["params"]["slow"]).mean().iloc[-1]
        signal = "buy" if ma_f > ma_s else "sell"
    else:
        n = strategy_data["params"]["n"]
        mid = df["close"].rolling(n).mean().iloc[-1]
        std = df["close"].rolling(n).std().iloc[-1]
        up = mid + strategy_data["params"]["k"]*std
        dn = mid - strategy_data["params"]["k"]*std
        last = df["close"].iloc[-1]
        signal = "buy" if last < dn else ("sell" if last > up else "hold")

    return {"signal": signal, "size_pct": size_pct, "price": price}
