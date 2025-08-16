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
        self.win_count