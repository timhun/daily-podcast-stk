# run_pipeline.py
import os, json, shutil
from datetime import datetime
from src.data_fetch import fetch_ohlcv, add_indicators
from src.strategy_generator import make_weekly_report, generate_strategy_file
from src.backtest import run_backtest
from src.risk import decide_deploy
from src.daily_sim import run_daily_sim

SYMBOL = "0050.TW"
YEARS  = 3
REPORT_DIR = "reports"
STRAT_OUT = "strategy_candidate.py"   # 固定放在 repo root，供 daily job 使用
FALLBACK_SRC = "src/strategy_default.py"

os.makedirs(REPORT_DIR, exist_ok=True)

def weekly_pipeline():
    print("=== 1) 拉資料 + 指標 ===")
    df = fetch_ohlcv(SYMBOL, years=YEARS)
    df = add_indicators(df)

    print("\n=== 2) 生成週報 & 策略碼 ===")
    weekly = make_weekly_report(df)
    with open(os.path.join(REPORT_DIR, "weekly_insight.json"), "w", encoding="utf-8") as f:
        json.dump(weekly, f, ensure_ascii=False, indent=2)

    # 產生策略（暫存在任意位置），generate_strategy_file 回傳檔案路徑
    temp_path = generate_strategy_file(weekly, out_path=STRAT_OUT + ".tmp")
    # move to repo root (overwrite)
    shutil.move(temp_path, STRAT_OUT)
    print(f"策略已寫入：{STRAT_OUT}")

    print("\n=== 3) 回測（含 OOS 留出 6 個月）===")
    metrics = run_backtest(df, strategy_path=STRAT_OUT,
                           commission_bps=2, slippage_bps=5, oos_months=6, out_dir=REPORT_DIR)
    with open(os.path.join(REPORT_DIR, "backtest_report.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print("\n=== 4) 風控決策 ===")
    decision = decide_deploy(metrics, min_sharpe=1.0, max_mdd=0.20, min_trades=10)
    decision["asof"] = datetime.utcnow().isoformat()
    with open(os.path.join(REPORT_DIR, "deployment_decision.json"), "w", encoding="utf-8") as f:
        json.dump(decision, f, indent=2)
    print("部署決策：", decision)

    return decision

def daily_job():
    # daily 用 run_daily_sim，若找不到 strategy_candidate.py 則 daily_sim 會 fallback
    print("=== DAILY JOB ===")
    res = run_daily_sim(SYMBOL, strategy_path=STRAT_OUT, cash=1_000_000)
    with open(os.path.join(REPORT_DIR, "last_daily_signal.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    return res

if __name__ == "__main__":
    import sys
    if len(sys.argv)>1 and sys.argv[1].lower()=="daily":
        print(daily_job())
    else:
        print(weekly_pipeline())