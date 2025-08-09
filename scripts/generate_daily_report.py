#!/usr/bin/env python3
# scripts/generate_daily_report.py
import os
import datetime
import pandas as pd
import yfinance as yf
from notion_client import Client

# ===== 設定 =====
TICKERS = {
    "QQQ": "QQQ",
    "0050": "0050.TW"
}

START = datetime.date.today() - datetime.timedelta(days=730)  # 近兩年
TODAY = datetime.date.today()
REPORT_FILE = "daily_report.md"

# 從環境變數讀取 Notion 認證資訊
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# 簡單檢查
if not NOTION_TOKEN:
    print("Error: NOTION_TOKEN 未設定或為空")
    exit(1)
if not NOTION_DATABASE_ID:
    print("Error: NOTION_DATABASE_ID 未設定或為空")
    exit(1)

# 建立 Notion client
try:
    notion = Client(auth=NOTION_TOKEN)
    print("Notion Client 初始化成功")
except Exception as e:
    print(f"Notion Client 初始化失敗: {e}")
    exit(1)

# ===== 下載股價資料 =====
def fetch_df(ticker):
    df = yf.download(
        ticker,
        start=START.strftime("%Y-%m-%d"),
        end=(TODAY + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        progress=False
    )
    df = df.dropna()
    return df

# ===== 回測策略：移動平均 =====
def backtest_ma(df, short_window, long_window):
    if len(df) < long_window + 2:
        return None
    df["MA_S"] = df["Close"].rolling(window=short_window).mean()
    df["MA_L"] = df["Close"].rolling(window=long_window).mean()
    df["Signal"] = 0
    df.loc[df["MA_S"] > df["MA_L"], "Signal"] = 1
    df["Position"] = df["Signal"].diff()
    trades = df[df["Position"] != 0]
    if trades.empty:
        return None
    returns = (df["Close"].pct_change() * df["Signal"].shift(1)).dropna()
    win_rate = (returns > 0).sum() / len(returns)
    return {"type": "MA", "params": (short_window, long_window), "win_rate": win_rate}

# ===== 回測策略：均值回歸 =====
def backtest_mean_reversion(df, lookback=5, k=2):
    if len(df) < lookback + 1:
        return None
    m = df["Close"].rolling(window=lookback).mean()
    sdev = df["Close"].rolling(window=lookback).std()
    signal = df["Close"] < (m - k * sdev)
    returns = (df["Close"].pct_change().shift(-1) * signal).dropna()
    if returns.empty:
        return None
    win_rate = (returns > 0).sum() / len(returns)
    return {"type": "MR", "params": (lookback, f"k={k}"), "win_rate": win_rate}

# ===== 找出最佳策略 =====
def pick_best_strategy(df):
    strategies = []
    for s, l in [(5, 20), (10, 50), (20, 100)]:
        res = backtest_ma(df, s, l)
        if res:
            strategies.append(res)
    for k in [1, 1.5, 2]:
        res = backtest_mean_reversion(df, lookback=5, k=k)
        if res:
            strategies.append(res)
    if not strategies:
        return None
    return max(strategies, key=lambda x: x["win_rate"])

# ===== 當日訊號判斷 =====
def today_signal(df, strategy):
    try:
        if strategy["type"] == "MA":
            s, l = strategy["params"]
            if len(df) < l + 2:
                return "資料不足"
            ma_s = df['Close'].rolling(window=s).mean()
            ma_l = df['Close'].rolling(window=l).mean()
            last = len(df) - 1
            cond = (ma_s.iloc[last] > ma_l.iloc[last]) and (ma_s.iloc[last-1] <= ma_l.iloc[last-1])
            return "買入" if cond else "無信號"

        elif strategy["type"] == "MR":
            lookback = 5
            k = float(strategy["params"][1].split("=")[1])
            if len(df) < lookback + 1:
                return "資料不足"
            m = df['Close'].rolling(window=lookback).mean()
            sdev = df['Close'].rolling(window=lookback).std()
            last = len(df) - 1
            if pd.isna(m.iloc[last]) or pd.isna(sdev.iloc[last]):
                return "資料不足"
            cond = df['Close'].iloc[last] < m.iloc[last] - k * sdev.iloc[last]
            return "買入" if cond else "無信號"

        else:
            return "策略類型錯誤"
    except Exception as e:
        return f"計算錯誤: {e}"

# ===== 產生 Markdown =====
def make_markdown(results):
    md = [f"# 每日策略報告 ({TODAY.isoformat()})\n"]
    for name, info in results.items():
        md.append(f"## {name}\n")
        if not info["best"]:
            md.append(f"- **狀態**：{info['signal']}\n")
            continue
        md.append(f"- **選擇的策略類型**：{info['best']['type']}\n")
        md.append(f"- **策略參數**：{info['best']['params']}\n")
        md.append(f"- **歷史勝率**：{info['best']['win_rate']:.2%}\n")
        md.append(f"- **當日訊號**：{info['signal']}\n")
        md.append("")
    return "\n".join(md)

# ===== 寫入 Notion =====
def create_notion_page(title, content):
    try:
        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Name": {"title": [{"text": {"content": title}}]}
            },
            children=[
                {"object": "block", "type": "paragraph", "paragraph": {"text": [{"type": "text", "text": {"content": content}}]}}
            ]
        )
        print("Notion 頁面建立成功")
    except Exception as e:
        print(f"建立 Notion 頁面失敗: {e}")

# ===== 主程式 =====
def main():
    results = {}
    for name, ticker in TICKERS.items():
        try:
            df = fetch_df(ticker)
            if df.shape[0] < 30:
                results[name] = {"best": None, "signal": "資料不足"}
                continue
            best = pick_best_strategy(df)
            if not best:
                results[name] = {"best": None, "signal": "策略計算錯誤"}
                continue
            sig = today_signal(df, best)
            results[name] = {"best": best, "signal": sig}
        except Exception as e:
            results[name] = {"best": None, "signal": f"錯誤: {e}"}

    md = make_markdown(results)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(md)
    title = f"每日策略報告 {TODAY.isoformat()}"
    create_notion_page(title, md)
    print("Report generated:", REPORT_FILE)

if __name__ == "__main__":
    main()