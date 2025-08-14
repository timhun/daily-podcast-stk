# src/daily_sim.py
import importlib.util, os, csv, shutil
from datetime import datetime
from src.data_fetch import fetch_ohlcv, add_indicators

LOG_PATH = "reports/daily_trades.csv"
STRAT_PATH = "strategy_candidate.py"
FALLBACK_PATH = "src/strategy_default.py"

def _ensure_log():
    os.makedirs(os.path.dirname(LOG_PATH) or ".", exist_ok=True)
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["time","symbol","signal","price","size","note"])

def _ensure_strategy():
    """
    如果 root 沒有 strategy_candidate.py，嘗試從 src/strategy_default.py 複製過去，
    並回傳一個 note 字串說明來源（被 daily 使用時可寫入日誌）。
    """
    if os.path.exists(STRAT_PATH):
        return "loaded_from_repo"
    # fallback: copy default
    if os.path.exists(FALLBACK_PATH):
        shutil.copyfile(FALLBACK_PATH, STRAT_PATH)
        return "fallback_from_default"
    return "no_strategy_available"

def _load_strategy_module(strategy_path: str):
    spec = importlib.util.spec_from_file_location("strategy_candidate", strategy_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def run_daily_sim(symbol="0050.TW", strategy_path=STRAT_PATH, cash=1_000_000):
    _ensure_log()
    note = _ensure_strategy()
    if note == "no_strategy_available":
        raise FileNotFoundError("No strategy_candidate.py and no fallback available.")
    df = fetch_ohlcv(symbol, years=1)
    df = add_indicators(df)
    # import strategy
    mod = _load_strategy_module(strategy_path)
    Strat = mod.StrategyCandidate
    sig = Strat.generate_signal(df)
    price = float(df["close"].iloc[-1])
    size = int((cash * sig.get("size_pct", 0.5)) / price) if sig.get("signal")=="buy" else 0
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([datetime.utcnow().isoformat(), symbol, sig.get("signal"), f"{price:.2f}", size, note])
    return {"signal": sig, "price": price, "size": size, "note": note}