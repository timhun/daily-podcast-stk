#!/usr/bin/env python3
# run_pipeline.py
import os
import datetime
from src.data_fetch import fetch_ohlcv
from src.daily_sim import run_daily_sim
from src.backtest import run_backtest
from src.notify import send_to_notion, send_to_slack

SYMBOL = "QQQ"
STRAT_OUT = "strategy_out.py"
CASH = 1_000_000


def daily_pipeline():
    print("=== [Daily Job] 模擬交易 ===")
    df = fetch_ohlcv(SYMBOL, years=1)
    res = run_daily_sim(SYMBOL, strategy_path="strategy_candidate.py", cash=CASH)

    msg = f"📊 Daily Sim {datetime.date.today()} | PnL={res['pnl']:.2f} | Pos={res['position']}"
    print(msg)

    # 存檔
    with open("signal.json", "w") as f:
        f.write(str(res))

    # 通知
    send_to_notion(res, db_id=os.getenv("NOTION_DB"), token=os.getenv("NOTION_TOKEN"))
    send_to_slack(msg, webhook=os.getenv("SLACK_WEBHOOK"))
    return res


def weekly_pipeline():
    print("=== [Weekly Job] 回測 + 更新策略 ===")
    df = fetch_ohlcv(SYMBOL, years=5)
    metrics = run_backtest(df, strategy_path=STRAT_OUT, cash=CASH)

    msg = f"📈 Weekly Backtest done. Sharpe={metrics['sharpe']:.2f}, MaxDD={metrics['maxdd']:.2%}"
    print(msg)

    send_to_notion(metrics, db_id=os.getenv("NOTION_DB"), token=os.getenv("NOTION_TOKEN"))
    send_to_slack(msg, webhook=os.getenv("SLACK_WEBHOOK"))
    return metrics


if __name__ == "__main__":
    mode = os.getenv("JOB_MODE", "daily")  # 預設 daily，可由 Actions 傳入 weekly
    if mode == "daily":
        daily_pipeline()
    elif mode == "weekly":
        weekly_pipeline()
    else:
        raise ValueError(f"Unknown JOB_MODE={mode}")
