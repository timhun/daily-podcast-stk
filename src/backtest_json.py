# src/backtest_json.py
# src/backtest_json.py
import json
import pandas as pd
from pathlib import Path
from .backtest import run_backtest


def _load_strategy(strategy_file: str):
    """讀取策略 JSON 檔"""
    with open(strategy_file, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_data(data_file: str, freq: str):
    """讀取資料 CSV，支援 daily / hourly"""
    df = pd.read_csv(data_file)

    if freq == "hourly":
        if "datetime" not in df.columns:
            raise ValueError("hourly 模式需要 datetime 欄位")
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)
    else:
        if "date" not in df.columns:
            raise ValueError("daily 模式需要 date 欄位")
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)

    return df


def run_backtest_json(strategy_file: str, data_file: str, freq: str = "daily"):
    """
    回測策略 JSON，輸出回測結果 JSON 檔案
    freq: 'daily' or 'hourly'
    """
    strategy = _load_strategy(strategy_file)
    df = _load_data(data_file, freq)

    report = run_backtest(df, strategy)

    Path("reports").mkdir(parents=True, exist_ok=True)
    output_path = Path("reports/backtest_report.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def run_daily_sim_json(data_file: str, strategy_file: str, freq: str = "daily"):
    """
    模擬策略（不改歷史資料），輸出 JSON 檔案
    freq: 'daily' or 'hourly'
    """
    strategy = _load_strategy(strategy_file)
    df = _load_data(data_file, freq)

    report = run_backtest(df, strategy, simulate_only=True)

    Path("reports").mkdir(parents=True, exist_ok=True)
    output_path = Path("reports/daily_sim.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report
