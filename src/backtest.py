# src/backtest.py
import importlib.util, backtrader as bt, pandas as pd
from dateutil.relativedelta import relativedelta
import os, json

class PandasDataTZ(bt.feeds.PandasData):
    params = (('datetime', None),)

class BridgeStrategy(bt.Strategy):
    """Call StrategyCandidate.generate_signal from pandas slice (headless)"""
    params = dict(stop_loss=0.08)

    def __init__(self):
        self._df = self.data._dataname
        self.entry_price = None

    def next(self):
        # current datetime as string
        cur_dt = str(self.data.datetime.date(0))
        slice_df = self._df.loc[:cur_dt].copy()
        from strategy_candidate import StrategyCandidate
        sig = StrategyCandidate.generate_signal(slice_df)
        # simple execution logic
        if not self.position and sig["signal"] == "buy":
            cash = self.broker.getcash()
            price = self.data.close[0]
            size = int((cash * sig.get("size_pct", 0.5)) / price)
            if size > 0:
                self.buy(size=size)
                self.entry_price = price
        elif self.position:
            price = self.data.close[0]
            if self.entry_price and price <= self.entry_price * (1 - self.p.stop_loss):
                self.close(); self.entry_price = None
            elif sig["signal"] == "sell":
                self.close(); self.entry_price = None

def _split_oos(df: pd.DataFrame, oos_months=6):
    split_dt = df.index.max() - relativedelta(months=oos_months)
    return df[df.index <= split_dt], df[df.index > split_dt]

def run_backtest(df: pd.DataFrame, strategy_path: str = "strategy_candidate.py",
                 commission_bps=2, slippage_bps=5, oos_months=6, out_dir="reports"):
    os.makedirs(out_dir, exist_ok=True)
    # ensure strategy file present in workspace
    # copy strategy_path to workspace root as strategy_candidate.py for import
    import shutil
    shutil.copyfile(strategy_path, "strategy_candidate.py")

    train_df, oos_df = _split_oos(df, oos_months=oos_months)

    def _run_once(dataframe):
        cerebro = bt.Cerebro()
        bt_data = PandasDataTZ(dataname=dataframe)
        cerebro.adddata(bt_data)
        cerebro.addstrategy(BridgeStrategy)
        cerebro.broker.setcash(1_000_000)
        cerebro.broker.setcommission(commission=commission_bps/10000)
        cerebro.broker.set_slippage_perc(perc=slippage_bps/10000)
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='dd')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='ta')
        res = cerebro.run(maxcpus=1)[0]
        sharpe = res.analyzers.sharpe.get_analysis().get('sharperatio', 0) or 0.0
        dd_raw = res.analyzers.dd.get_analysis()
        max_dd = getattr(dd_raw, "max", {}).get("drawdown", 0) if isinstance(dd_raw, dict) else (dd_raw.max.drawdown if hasattr(dd_raw,'max') else 0)
        ta = res.analyzers.ta.get_analysis()
        trades = 0
        winrate = 0.0
        try:
            trades = int(ta.total.closed)
            winrate = float(ta.won.total)/trades if trades>0 else 0.0
        except Exception:
            pass
        end_value = cerebro.broker.getvalue()
        return dict(end_value=end_value, sharpe=sharpe, mdd=max_dd/100.0 if max_dd>1 else max_dd, trades=trades, winrate=winrate)

    train_metrics = _run_once(train_df)
    oos_metrics   = _run_once(oos_df)
    out = {"train": train_metrics, "oos": oos_metrics, "meta": {"oos_months": oos_months}}
    with open(os.path.join(out_dir, "backtest_report.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    return out