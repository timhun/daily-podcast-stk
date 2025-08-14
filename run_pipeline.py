# run_pipeline.py
import json, os
from src.data_fetch import fetch_ohlcv, add_indicators
from src.strategy_generator import make_weekly_report, generate_strategy_file
from src.backtest import run_backtest
from src.risk import decide_deploy
from src.daily_sim import run_daily_sim

SYMBOL="0050.TW"
OUT_DIR="reports"
os.makedirs(OUT_DIR, exist_ok=True)

def weekly_pipeline():
    df = fetch_ohlcv(SYMBOL, years=3)
    df = add_indicators(df)
    weekly = make_weekly_report(df)
    with open(os.path.join(OUT_DIR,"weekly_insight.json"), "w", encoding="utf-8") as f:
        json.dump(weekly, f, indent=2, ensure_ascii=False)
    strat_file = generate_strategy_file(weekly, out_path="strategy_candidate.py")
    metrics = run_backtest(df, strategy_path=strat_file, oos_months=6, out_dir=OUT_DIR)
    decision = decide_deploy(metrics, min_sharpe=1.0, max_mdd=0.20, min_trades=10)
    with open(os.path.join(OUT_DIR,"deployment_decision.json"), "w", encoding="utf-8") as f:
        json.dump(decision, f, indent=2, ensure_ascii=False)
    return decision

def daily_job():
    res = run_daily_sim(SYMBOL, strategy_path="strategy_candidate.py", cash=1_000_000)
    with open(os.path.join(OUT_DIR,"last_daily_signal.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    return res

if __name__ == "__main__":
    import sys
    if len(sys.argv)>1 and sys.argv[1]=="daily":
        print(daily_job())
    else:
        print(weekly_pipeline())