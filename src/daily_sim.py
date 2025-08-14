# src/daily_sim.py
import importlib.util, os, csv
from datetime import datetime
from src.data_fetch import fetch_ohlcv, add_indicators

LOG_PATH = "reports/daily_trades.csv"

def _ensure_log():
    os.makedirs(os.path.dirname(LOG_PATH) or ".", exist_ok=True)
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["time","symbol","signal","price","size"])

def run_daily_sim(symbol="0050.TW", strategy_path="strategy_candidate.py", cash=1_000_000):
    _ensure_log()
    df = fetch_ohlcv(symbol, years=1)
    df = add_indicators(df)
    # import strategy
    spec = importlib.util.spec_from_file_location("strategy_candidate", strategy_path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    Strat = mod.StrategyCandidate
    sig = Strat.generate_signal(df)
    price = float(df["close"].iloc[-1])
    size = int((cash * sig.get("size_pct", 0.5)) / price) if sig.get("signal")=="buy" else 0
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([datetime.utcnow().isoformat(), symbol, sig.get("signal"), f"{price:.2f}", size])
    return {"signal": sig, "price": price, "size": size}