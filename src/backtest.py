import backtrader as bt
import pandas as pd
import importlib.util
import os
import shutil

class PandasData(bt.feeds.PandasData):
    params = (
        ('datetime', None),
        ('open', -1),
        ('high', -1),
        ('low', -1),
        ('close', -1),
        ('volume', -1),
        ('openinterest', None),
    )

def run_backtest(df, strategy_path, cash=1_000_000, commission=0.001, oos_months=6):
    """
    執行回測，並回傳績效指標 dict。
    會自動留出最近 oos_months 個月做 OOS 測試。
    """
    # 分割資料成 in-sample 與 out-of-sample
    df = df.sort_index()
    split_point = df.index[-1] - pd.DateOffset(months=oos_months)
    df_train = df[df.index <= split_point]
    df_test = df[df.index > split_point]

    # 匯入策略模組
    spec = importlib.util.spec_from_file_location("CustomStrategy", strategy_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    StrategyClass = mod.CustomStrategy

    # 只在來源與目標不同時才複製策略檔
    if os.path.abspath(strategy_path) != os.path.abspath("strategy_candidate.py"):
        shutil.copyfile(strategy_path, "strategy_candidate.py")

    # === In-Sample 回測 ===
    cerebro_train = bt.Cerebro()
    cerebro_train.addstrategy(StrategyClass)
    data_train = PandasData(dataname=df_train)
    cerebro_train.adddata(data_train)
    cerebro_train.broker.setcash(cash)
    cerebro_train.broker.setcommission(commission=commission)
    cerebro_train.run()
    portfolio_train = cerebro_train.broker.getvalue()

    # === Out-of-Sample 測試 ===
    cerebro_test = bt.Cerebro()
    cerebro_test.addstrategy(StrategyClass)
    data_test = PandasData(dataname=df_test)
    cerebro_test.adddata(data_test)
    cerebro_test.broker.setcash(portfolio_train)
    cerebro_test.broker.setcommission(commission=commission)
    cerebro_test.run()
    portfolio_test = cerebro_test.broker.getvalue()

    # 計算績效
    total_return = (portfolio_test - cash) / cash
    annual_return = total_return / (len(df) / 252)  # 252 交易日/年
    max_drawdown = (df['close'].cummax() - df['close']).max() / df['close'].cummax().max()
    sharpe_ratio = (annual_return - 0.02) / (df['close'].pct_change().std() * (252 ** 0.5))

    metrics = {
        "in_sample_final_value": portfolio_train,
        "out_sample_final_value": portfolio_test,
        "total_return": total_return,
        "annual_return": annual_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio
    }

    return metrics