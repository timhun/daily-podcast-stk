import os, json, datetime
from src.data_fetch import fetch_ohlcv, add_indicators
from src.strategy_generator import make_weekly_report, generate_strategy_file
from src.backtest import run_backtest
from src.daily_sim import run_daily_sim

SYMBOL = "0050.TW"
OUT_DIR = "reports"
STRAT_OUT = "strategy_candidate.py"
HISTORY_FILE = "strategy_history.json"

os.makedirs(OUT_DIR, exist_ok=True)

def _load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def _save_history(hist):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=2, ensure_ascii=False)

def weekly_pipeline():
    print("=== Weekly Pipeline ===")
    df = fetch_ohlcv(SYMBOL, years=3)
    df = add_indicators(df)
    weekly = make_weekly_report(df)
    with open(os.path.join(OUT_DIR,"weekly_insight.json"), "w", encoding="utf-8") as f:
        json.dump(weekly, f, indent=2, ensure_ascii=False)

    # 1) 先用 rule-based 生成一版
    generate_strategy_file(weekly, out_path=STRAT_OUT)

    # 2) 可選：Groq LLM 再生成覆蓋
    use_llm = os.getenv("USE_LLM", "0") == "1" and os.getenv("GROQ_API_KEY")
    if use_llm:
        try:
            from src.strategy_llm_groq import generate_strategy_with_groq
            weekly_json = json.dumps(weekly, ensure_ascii=False)
            history_json = json.dumps(_load_history(), ensure_ascii=False)
            code = generate_strategy_with_groq(weekly_json, history_json)
            # 覆蓋策略檔
            with open(STRAT_OUT, "w", encoding="utf-8") as f:
                f.write(code)
            print("Groq LLM 已生成並覆蓋策略。")
        except Exception as e:
            print("Groq 生成失敗，保留 rule-based 策略。", e)

    # 3) 回測
    metrics = run_backtest(df, strategy_path=STRAT_OUT, cash=1_000_000)
    with open(os.path.join(OUT_DIR,"backtest_report.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    # 4) 更新記憶庫
    hist = _load_history()
    hist.append({
        "date": datetime.date.today().isoformat(),
        "strategy_file": STRAT_OUT,
        "metrics": metrics
    })
    _save_history(hist)

    return metrics

def daily_pipeline():
    print("=== Daily Simulation ===")
    res = run_daily_sim(SYMBOL, strategy_path=STRAT_OUT, cash=1_000_000)
    with open(os.path.join(OUT_DIR,"last_daily_signal.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)

    # 另外輸出簡短文字檔，方便 workflow 讀取
    try:
        sig = res.get("signal", {}).get("signal", "hold")
        price = res.get("price", 0.0)
        size = res.get("size", 0)
        with open(os.path.join(OUT_DIR,"daily_signal.txt"), "w", encoding="utf-8") as f:
            f.write(str(sig))
        with open(os.path.join(OUT_DIR,"daily_price.txt"), "w", encoding="utf-8") as f:
            f.write(f"{price:.2f}")
        with open(os.path.join(OUT_DIR,"daily_size.txt"), "w", encoding="utf-8") as f:
            f.write(str(size))
    except Exception as e:
        print("寫 daily 簡報檔失敗：", e)
    return res

if __name__ == "__main__":
    weekday = datetime.date.today().weekday()
    if weekday == 5:      # Sat -> Weekly
        weekly_pipeline()
    elif weekday < 5:     # Mon-Fri -> Daily
        daily_pipeline()
    else:                 # Sun -> no op
        print("Sunday: no task")
