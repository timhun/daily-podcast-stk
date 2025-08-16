#quantity_strategy_0050.py
import backtrader as bt
import pandas as pd
import json
import os
from datetime import datetime
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuantityStrategy(bt.Strategy):
    params = (
        ('volume_ma_period', 5),  # 成交量均線週期
        ('volume_multiplier', 1.5),  # 量增閾值
        ('stop_profit', 0.015),  # 停利 1.5%
        ('stop_loss', 0.025),  # 停損 2.5%
        ('risk_per_trade', 0.02),  # 單筆風險 < 2%
    )

    def __init__(self):
        self.volume_ma = bt.indicators.SMA(self.data.volume, period=self.params.volume_ma_period)
        self.order = None
        self.entry_price = 0
        self.trades = []

    def next(self):
        try:
            # 檢查數據有效性
            if len(self.data) < self.params.volume_ma_period:
                return
                
            volume_rate = self.data.volume[0] / self.volume_ma[0] if self.volume_ma[0] > 0 else 0
            current_price = float(self.data.close[0])
            
            # ... rest of logic
        except Exception as e:
            logger.error(f"策略執行錯誤: {e}")
            logger.error(traceback.format_exc())
        signal = "無訊號"

        if self.order:
            return

        if not self.position:
            if volume_rate > self.params.volume_multiplier and self.data.close[0] > self.data.close[-1]:
                size = min(
                    self.broker.getcash() / current_price * self.params.risk_per_trade / self.params.stop_loss,
                    self.broker.getcash() / current_price
                )
                self.order = self.buy(size=int(size))
                self.entry_price = current_price
                signal = "買入"
                logger.info(f"{self.data.datetime.date(0)} 買入: 價格={current_price:.2f}, 量增率={volume_rate:.2f}")
        else:
            if volume_rate < 1 and self.data.close[0] < self.data.close[-1]:
                self.order = self.sell(size=self.position.size)
                signal = "賣出 (量縮價跌)"
            elif self.data.close[0] >= self.entry_price * (1 + self.params.stop_profit):
                self.order = self.sell(size=self.position.size)
                signal = "賣出 (停利)"
            elif self.data.close[0] <= self.entry_price * (1 - self.params.stop_loss):
                self.order = self.sell(size=self.position.size)
                signal = "賣出 (停損)"

        # 儲存每日模擬訊號
        if self.data.datetime.date(0) == self.data.datetime.date(-1):
            daily_sim = {
                "date": str(self.data.datetime.date(0)),
                "signal": signal,
                "price": round(current_price, 2),
                "volume_rate": round(volume_rate, 2),
                "size_pct": round(self.params.risk_per_trade, 3)
            }
            os.makedirs("data", exist_ok=True)
            with open("data/daily_sim.json", "w", encoding="utf-8") as f:
                json.dump(daily_sim, f, ensure_ascii=False, indent=2)
            logger.info("已保存 daily_sim.json")

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trades.append(trade.pnl > 0)

    def stop(self):
        win_rate = sum(1 for t in self.trades if t) / len(self.trades) if self.trades else 0
        final_value = self.broker.getvalue()
        pnl = final_value - 1000000
        sharpe = self.analyzers.sharpe_ratio.get_analysis().get('sharperatio', 'N/A')
        cagr = self.analyzers.returns.get_analysis()['rnorm100']
        drawdown = self.analyzers.drawdown.get_analysis()['max']['drawdown']
        
        report = {
            "metrics": {
                "initial_cash": 1000000,
                "final_value": round(final_value, 2),
                "pnl": round(pnl, 2),
                "cagr": round(cagr, 2),
                "max_drawdown": round(drawdown, 2),
                "sharpe_ratio": sharpe if sharpe != 'N/A' else None,
                "win_rate": round(win_rate, 3),
                "total_trades": len(self.trades)
            }
        }
        with open("data/backtest_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info("已保存 backtest_report.json")

        # 更新策略歷史
        history_entry = {
            "date": str(datetime.now().date()),
            "strategy": {"signal": report["metrics"]["win_rate"]},
            "sharpe": sharpe,
            "mdd": round(drawdown, 2)
        }
        history_file = "data/strategy_history.json"
        history = []
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        history.append(history_entry)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history[-5:], f, ensure_ascii=False, indent=2)
        logger.info("已保存 strategy_history.json")

def run_backtest():
    data_file = 'data/daily_0050.csv'
    try:
        # 檢查檔案是否存在
        if not os.path.exists(data_file):
            logger.error(f"找不到數據檔案: {data_file}")
            return
            
        # 讀取數據
        daily_df = pd.read_csv(data_file)
        
        # 檢查必要欄位
        required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        missing_columns = [col for col in required_columns if col not in daily_df.columns]
        if missing_columns:
            logger.error(f"缺少必要欄位: {missing_columns}")
            return
        
        if daily_df.empty:
            logger.error(f"{data_file} 中無數據，跳過回測")
            return
            
        # 數據預處理 - 重要：移除 Symbol 欄位並確保數值型態
        daily_df['Date'] = pd.to_datetime(daily_df['Date'])
        daily_df = daily_df.sort_values('Date').reset_index(drop=True)
        
        # 只保留數值欄位，移除 Symbol 欄位
        numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_columns:
            daily_df[col] = pd.to_numeric(daily_df[col], errors='coerce')
        
        # 移除有缺失值的行
        daily_df = daily_df.dropna(subset=numeric_columns)
        
        if daily_df.empty:
            logger.error("清理後無有效數據")
            return
        
        # 確保有 Adj Close 欄位
        if 'Adj Close' not in daily_df.columns:
            daily_df['Adj Close'] = daily_df['Close']
        else:
            daily_df['Adj Close'] = pd.to_numeric(daily_df['Adj Close'], errors='coerce')
            daily_df['Adj Close'] = daily_df['Adj Close'].fillna(daily_df['Close'])
        
        # 準備 backtrader 數據 - 只包含數值欄位
        daily_df_bt = daily_df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
        daily_df_bt = daily_df_bt.set_index('Date')
        
        # 檢查數據完整性
        if len(daily_df_bt) < 10:
            logger.warning(f"數據量過少（{len(daily_df_bt)}筆），回測結果可能不準確")
        
        logger.info(f"準備回測數據: {len(daily_df_bt)} 筆，時間範圍: {daily_df_bt.index[0]} 到 {daily_df_bt.index[-1]}")
        
        # 設定 cerebro
        cerebro = bt.Cerebro()
        cerebro.addstrategy(QuantityStrategy)
        
        # 添加數據 - 使用正確的欄位映射
        data = bt.feeds.PandasData(
            dataname=daily_df_bt,
            datetime=None,  # 使用索引作為時間
            open='Open', high='High', low='Low', close='Close', volume='Volume',
            openinterest=None  # 不使用 openinterest
        )
        cerebro.adddata(data)
        
        # 設定初始資金和手續費
        cerebro.broker.setcash(1000000)
        cerebro.broker.setcommission(commission=0.001)  # 0.1% 手續費
        
        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio', riskfreerate=0.01)
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        
        logger.info("開始回測...")
        
        # 執行回測
        results = cerebro.run()
        
        logger.info("回測完成，報告已保存至 data/")
        
    except Exception as e:
        logger.error(f"回測失敗: {e}")
        logger.error(traceback.format_exc())
        
        # 創建錯誤報告
        error_report = {
            "metrics": {
                "initial_cash": 1000000,
                "final_value": 1000000,
                "pnl": 0,
                "cagr": 0,
                "max_drawdown": 0,
                "sharpe_ratio": None,
                "win_rate": 0,
                "total_trades": 0,
                "error": str(e)
            }
        }
        os.makedirs("data", exist_ok=True)
        with open("data/backtest_report.json", "w", encoding="utf-8") as f:
            json.dump(error_report, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    run_backtest()
