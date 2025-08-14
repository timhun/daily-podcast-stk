# src/risk.py
def decide_deploy(metrics: dict, min_sharpe=1.0, max_mdd=0.20, min_trades=10):
    oos = metrics.get("oos", {})
    ok = (oos.get("sharpe", 0) >= min_sharpe
          and oos.get("mdd", 1) <= max_mdd
          and oos.get("trades", 0) >= min_trades)
    reason = None if ok else f"未達門檻: Sharpe>={min_sharpe}, MDD<={max_mdd}, trades>={min_trades}"
    return {"accept": ok, "reason": reason, "oos": oos, "train": metrics.get("train", {})}