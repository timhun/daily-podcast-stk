import os
import datetime
from src.data_fetch import fetch_ohlcv
from src.strategy_gen import generate_strategy
from src.backtest import run_backtest
from src.daily_sim import run_daily_sim

SYMBOL = "0050.TW"
STRAT_OUT = "strategy_candidate.py"

def weekly_pipeline():
    print("=== 1) 拉資料 + 指標 ===")
    df = fetch_ohlcv(SYMBOL, years=3)

    print("\n=== 2) 生成週報 & 策略碼 ===")
    strategy_code = generate_strategy(df)
    with open(STRAT_OUT, "w", encoding="utf-8") as f:
        f.write(strategy_code)
    print(f"策略已寫入：{STRAT_OUT}")

    print("\n=== 3) 回測（含 OOS 留出 6 個月）===")
    metrics = run_backtest(df, strategy_path=STRAT_OUT, cash=1_000_000)
    print("回測績效：", metrics)

    # 簡單判斷是否部署
    if metrics["sharpe_ratio"] > 1.0 and metrics["max_drawdown"] < 0.2:
        print("策略通過，進入每日模擬交易階段")
    else:
        print("策略未通過，將在下週重新生成")
    return metrics

def daily_job():
    print("=== 每日模擬交易 ===")
    res = run_daily_sim(SYMBOL, strategy_path=STRAT_OUT, cash=1_000_000)
    print("當日模擬結果：", res)
    return res

if __name__ == "__main__":
    today = datetime.date.today()
    weekday = today.weekday()

    if weekday == 5:  # 星期六跑 weekly pipeline
        print("=== 每週策略更新任務 ===")
        weekly_pipeline()
    elif weekday < 5:  # 週一到週五跑 daily job
        print("=== 每日交易任務 ===")
        daily_job()
    else:
        print("週日休市，無任務執行")