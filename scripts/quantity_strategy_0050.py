import backtrader as bt
import pandas as pd
import json
import os
from datetime import datetime
import logging
import traceback

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuantityStrategy(bt.Strategy):
    params = (
        ('volume_ma_period', 5),  # 成交量均線週期
        ('volume_multiplier', 1.2),  # 調整為 1.2，增加交易機會
        ('stop_profit', 0.02),  # 調整為 2%
        ('stop_loss', 0.02),  # 調整為 2%
        ('risk_per_trade', 0.02),  # 單筆風險 < 2%
        ('target_win_rate', 0.75),  # 目標勝率 75%
    )

    def __init__(self):
        self.volume_ma = bt.indicators.SMA(self.data.volume, period=self.params.volume_ma_period)
        self.order = None
        self.entry_price = 0
        self.trades = []
        self.daily_signals = []  # 儲存所有每日訊號
        self.win_count = 0
        self.total_trades = 0

    def next(self):
        try:
            # 檢查數據有效性
            if len(self.data) < self.params.volume_ma_period:
                return
                
            volume_rate = self.data.volume[0] / self.volume_ma[0] if self.volume_ma[0] > 0 else 0
            current_price = float(self.data.close[0])
            signal = "無訊號"

            if self.order:
                return

            if not self.position:
                # 確保有前一日數據
                if len(self.data) > 1 and volume_rate > self.params.volume_multiplier and self.data.close[0] > self.data.close[-1]:
                    size = min(
                        self.broker.getcash() / current_price * self.params.risk_per_trade / self.params.stop_loss,
                        self.broker.getcash() / current_price
                    )
                    if size > 0:
                        self.order = self.buy(size=int(size))
                        self.entry_price = current_price
                        signal = "買入"
                        logger.info(f"{self.data.datetime.date(0)} 買入: 價格={current_price:.2f}, 量增率={volume_rate:.2f}")
            else:
                if len(self.data) > 1:  # 確保有前一日數據
                    if volume_rate < 1 and self.data.close[0] < self.data.close[-1]:
                        self.order = self.sell(size=self.position.size)
                        signal = "賣出 (量縮價跌)"
                    elif self.data.close[0] >= self.entry_price * (1 + self.params.stop_profit):
                        self.order = self.sell(size=self.position.size)
                        signal = "賣出 (停利)"
                    elif self.data.close[0] <= self.entry_price * (1 - self.params.stop_loss):
                        self.order = self.sell(size=self.position.size)
                        signal = "賣出 (停損)"

            # 儲存每日訊號
            current_date = self.data.datetime.date(0)
            if len(self.daily_signals) == 0 or self.daily_signals[-1]['date'] != str(current_date):
                daily_sim = {
                    "date": str(current_date),
                    "signal": signal,
                    "price": round(current_price, 2),
                    "volume_rate": round(volume_rate, 2),
                    "size_pct": round(self.params.risk_per_trade, 3)
                }
                self.daily_signals.append(daily_sim)

        except Exception