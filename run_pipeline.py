#!/usr/bin/env python3
# run_pipeline.py
import json, os, datetime, argparse
from src.data_fetch import fetch_ohlcv
from src.strategy_llm_groq import generate_strategy_llm
from src.backtest import run_backtest
from src.daily_sim import run_daily_sim

parser = argparse.ArgumentParser()
parser.add_argument("--history_file", default="strategy_history.json")
parser.add_argument("--out_dir", default="reports")
args = parser.parse_args()

os.makedirs(args.out_dir, exist_ok=True)

# ---- 1. 取得歷史記錄 ----
if os.path.exists(args.history_file):
    with open(args.history_file, "r", encoding="utf-8") as f:
        history = json.load(f)
else:
    history = {"history": []}

# ---- 2. 拉資料 ----
SYMBOL = "0050.TW"
df = fetch_ohlcv(SYMBOL, years=3)

# ---- 3. LLM 自動生成策略 ----
strategy_data = generate_strategy_llm(df, history)
strategy_file_path = os.path.join(args.out_dir, "strategy_data.json")
with open(strategy_file_path, "w", encoding="utf-8") as f:
    json.dump(strategy_data, f, ensure_ascii=False, indent=2)

# ---- 4. 回測 ----
metrics = run_backtest(df, strategy_data)
metrics_file = os.path.join(args.out_dir, "backtest_report.json")
with open(metrics_file, "w", encoding="utf-8") as f:
    json.dump(metrics, f, ensure_ascii=False, indent=2)

# ---- 5. 每日模擬 ----
daily_res = run_daily_sim(SYMBOL, strategy_data)
for k, fname in zip(["signal", "price", "size"],
                    ["daily_signal.txt","daily_price.txt","daily_size.txt"]):
    with open(os.path.join(args.out_dir, fname), "w", encoding="utf-8") as f:
        f.write(str(daily_res.get(k,"N/A")))

# ---- 6. 更新策略歷史記錄 ----
history["history"].append({
    "date": str(datetime.date.today()),
    "strategy": strategy_data,
    "sharpe_ratio": metrics.get("sharpe_ratio"),
    "max_drawdown": metrics.get("max_drawdown")
})
with open(args.history_file, "w", encoding="utf-8") as f:
    json.dump(history, f, ensure_ascii=False, indent=2)
