import backtrader as bt
import pandas as pd

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

def run_backtest(df, strategy_path=None, strategy_data=None, cash=1_000_000, commission=0.001, oos_months=6):
    """
    strategy_data: JSON dict from LLM
    """
    df = df.sort_index()
    split_point = df.index[-1] - pd.DateOffset(months=oos_months)
    df_train = df[df.index <= split_point]
    df_test = df[df.index > split_point]

    # 定義動態策略類別
    class CustomStrategy(bt.Strategy):
        params = strategy_data.get("params", {})

        def next(self):
            signal_info = strategy_data.get("generate_signal", lambda df: {"signal":"hold"})(self.data)
            sig = signal_info.get("signal", "hold")
            size_pct = signal_info.get("size_pct", 0.5)
            cash_available = self.broker.getcash()
            if sig == "buy" and not self.position:
                self.buy(size=cash_available * size_pct / self.data.close[0])
            elif sig == "sell" and self.position:
                self.close()

    # In-sample
    cerebro_train = bt.Cerebro()
    cerebro_train.addstrategy(CustomStrategy)
    cerebro_train.adddata(PandasData(dataname=df_train))
    cerebro_train.broker.setcash(cash)
    cerebro_train.broker.setcommission(commission=commission)
    cerebro_train.run()
    portfolio_train = cerebro_train.broker.getvalue()

    # Out-of-sample
    cerebro_test = bt.Cerebro()
    cerebro_test.addstrategy(CustomStrategy)
    cerebro_test.adddata(PandasData(dataname=df_test))
    cerebro_test.broker.setcash(portfolio_train)
    cerebro_test.broker.setcommission(commission=commission)
    cerebro_test.run()
    portfolio_test = cerebro_test.broker.getvalue()

    total_return = (portfolio_test - cash) / cash
    annual_return = total_return / (len(df)/252)
    max_drawdown = (df['close'].cummax() - df['close']).max() / df['close'].cummax().max()
    sharpe_ratio = (annual_return - 0.02) / (df['close'].pct_change().std() * (252 ** 0.5))

    return {
        "in_sample_final_value": portfolio_train,
        "out_sample_final_value": portfolio_test,
        "total_return": total_return,
        "annual_return": annual_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio
    }
