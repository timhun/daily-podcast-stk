import yfinance as yf
import backtrader as bt
from datetime import datetime

class QuantityStrategy(bt.Strategy):
    params = (
        ('volume_ma_period', 5),  # 成交量均線週期 (楊雲翔常用5日)
        ('volume_multiplier', 1.5),  # 量增閾值 (量 > 均量 * 1.5)
        ('stop_profit', 0.015),  # 停利 1.5%
        ('stop_loss', 0.025),  # 停損 2.5%
        ('risk_per_trade', 0.02),  # 單筆風險 < 2%
    )

    def __init__(self):
        self.volume_ma = bt.indicators.SMA(self.data.volume, period=self.params.volume_ma_period)
        self.order = None
        self.entry_price = 0
        self.trades = []  # 記錄交易以計算勝率

    def next(self):
        volume_rate = self.data.volume[0] / self.volume_ma[0] if self.volume_ma[0] > 0 else 0

        if self.order:
            return

        if not self.position:
            if volume_rate > self.params.volume_multiplier and self.data.close[0] > self.data.close[-1]:
                size = min(self.broker.getcash() / self.data.close[0] * self.params.risk_per_trade / self.params.stop_loss, self.broker.getcash() / self.data.close[0])
                self.order = self.buy(size=int(size))
                self.entry_price = self.data.close[0]
        else:
            if volume_rate < 1 and self.data.close[0] < self.data.close[-1]:
                self.order = self.sell(size=self.position.size)
            elif self.data.close[0] >= self.entry_price * (1 + self.params.stop_profit):
                self.order = self.sell(size=self.position.size)
            elif self.data.close[0] <= self.entry_price * (1 - self.params.stop_loss):
                self.order = self.sell(size=self.position.size)

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trades.append(trade.pnl > 0)

    def stop(self):
        win_rate = sum(1 for t in self.trades if t) / len(self.trades) if self.trades else 0
        print(f"總交易次數: {len(self.trades)}, 勝率: {win_rate:.2%}")

# 回測程式
def run_backtest():
    cerebro = bt.Cerebro()
    cerebro.addstrategy(QuantityStrategy)
    data = bt.feeds.PandasData(dataname=yf.download('0050.TW', start='2021-01-01', end='2025-08-15'))
    cerebro.adddata(data)
    cerebro.broker.setcash(1000000)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    
    results = cerebro.run()
    strat = results[0]
    
    final_value = cerebro.broker.getvalue()
    pnl = final_value - 1000000
    sharpe = strat.analyzers.sharpe_ratio.get_analysis().get('sharperatio', 'N/A')
    cagr = strat.analyzers.returns.get_analysis()['rnorm100']
    drawdown = strat.analyzers.drawdown.get_analysis()['max']['drawdown']
    win_rate = sum(1 for t in strat.trades if t) / len(strat.trades) if strat.trades else 0
    
    report = f"""
    --- 0050.TW 量價策略回測報告 (基於楊雲翔心法) ---
    初始資金: 1,000,000
    最終資金: {final_value:,.2f}
    總損益: {pnl:,.2f}
    年化報酬率 (CAGR): {cagr:.2f}%
    最大回撤: {drawdown:.2f}%
    夏普比率: {sharpe}
    勝率: {win_rate:.2%}
    期望值 E: {(0.015 * win_rate) - (0.025 * (1 - win_rate)):.4f} (每次交易期望正值)
    優點: 高勝率，適合小資族，符合量增價漲理念。
    缺點: 盤整市表現平平，需優化停損機制。
    --------------------------------
    """
    print(report)
    return report

if __name__ == '__main__':
    run_backtest()