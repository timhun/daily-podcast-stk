#!/usr/bin/env python3
# scripts/generate_daily_report.py
import os, datetime, json
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from math import isnan

TODAY = datetime.datetime.utcnow().date()
START = TODAY - datetime.timedelta(days=730)  # 約 2 年
TICKERS = {"QQQ": "QQQ", "0050": "0050.TW"}

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID")
NOTION_VERSION = "2022-06-28"
REPORT_FILE = "daily_report.md"

def fetch_df(ticker):
    df = yf.download(ticker, start=START.strftime("%Y-%m-%d"), end=(TODAY + datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
    df = df.dropna()
    return df

def backtest_ma(df, short, long):
    df = df.copy()
    df['ma_s'] = df['Close'].rolling(window=short).mean()
    df['ma_l'] = df['Close'].rolling(window=long).mean()
    df['signal'] = ((df['ma_s'] > df['ma_l']) & (df['ma_s'].shift(1) <= df['ma_l'].shift(1))).astype(int)
    returns = []
    equity = [1.0]
    for i in range(len(df)-1):
        if df['signal'].iat[i] == 1:
            r = (df['Close'].iat[i+1] - df['Close'].iat[i]) / df['Close'].iat[i]
            returns.append(r)
            equity.append(equity[-1] * (1 + r))
    return calc_stats(returns, equity)

def backtest_mean_reversion(df, lookback=5, k=1.0):
    df = df.copy()
    df['m'] = df['Close'].rolling(window=lookback).mean()
    df['s'] = df['Close'].rolling(window=lookback).std()
    df['signal'] = ((df['Close'] < df['m'] - k*df['s'])).astype(int)
    returns = []
    equity = [1.0]
    for i in range(len(df)-1):
        if df['signal'].iat[i] == 1:
            r = (df['Close'].iat[i+1] - df['Close'].iat[i]) / df['Close'].iat[i]
            returns.append(r)
            equity.append(equity[-1] * (1 + r))
    return calc_stats(returns, equity)

def calc_stats(returns, equity):
    total = len(returns)
    wins = sum(1 for r in returns if r > 0)
    winrate = (wins/total*100) if total>0 else 0.0
    avg = np.mean(returns) if total>0 else 0.0
    cum = np.array(equity)
    peak = np.maximum.accumulate(cum)
    dd = np.max((peak - cum) / peak) if len(cum)>0 else 0.0
    return {"trades": total, "wins": wins, "winrate": round(winrate,2), "avg": round(avg*100,4), "mdd": round(dd*100,4), "equity": equity}

def pick_best_strategy(df):
    # 測試幾組 MA 參數
    ma_candidates = []
    for s in [3,5,8]:
        for l in [10,20,30]:
            if s < l:
                ma_candidates.append((s,l))
    best = {"type": None, "params": None, "stats": None}
    # test MA
    for s,l in ma_candidates:
        res = backtest_ma(df, s, l)
        if best["stats"] is None or res["winrate"] > best["stats"]["winrate"]:
            best.update({"type":"MA","params":(s,l),"stats":res})
    # test mean reversion (k values)
    for k in [0.8, 1.0, 1.2, 1.5]:
        res = backtest_mean_reversion(df, lookback=5, k=k)
        if res["winrate"] > best["stats"]["winrate"]:
            best.update({"type":"MR","params":("lookback=5","k="+str(k)),"stats":res})
    return best

def today_signal(df, strategy):
    # 基於最後一天資料判斷今日是否有信號 (以最後一列為最新)
    if strategy["type"] == "MA":
        s,l = strategy["params"]
        ma_s = df['Close'].rolling(window=s).mean()
        ma_l = df['Close'].rolling(window=l).mean()
        if len(df) < l: return "資料不足"
        last = len(df)-1
        cond = (ma_s.iat[last] > ma_l.iat[last]) and (ma_s.iat[last-1] <= ma_l.iat[last-1])
        return "買入" if cond else "無信號"
    else:
        # mean reversion
        lookback = 5
        k = float(strategy["params"][1].split("=")[1])
        m = df['Close'].rolling(window=lookback).mean()
        s = df['Close'].rolling(window=lookback).std()
        last = len(df)-1
        if pd.isna(m.iat[last]) or pd.isna(s.iat[last]): return "資料不足"
        cond = df['Close'].iat[last] < m.iat[last] - k * s.iat[last]
        return "買入" if cond else "無信號"

def make_markdown(results):
    md = []
    md.append(f"# 每日策略報告 — {TODAY.isoformat()}\n")
    for ticker, info in results.items():
        md.append(f"## {ticker}\n")
        md.append(f"- **選擇的策略類型**：{info['best']['type']}\n")
        md.append(f"- **參數**：{info['best']['params']}\n")
        st = info['best']['stats']
        md.append(f"- **近 2 年模擬交易（僅含有交易日）**：交易次數 {st['trades']} 次，勝率 {st['winrate']}%，平均單筆報酬 {st['avg']}%，最大回撤 {st['mdd']}%\n")
        md.append(f"- **今日判斷**：{info['signal']}\n")
        md.append("\n---\n")
    md.append("\n> 以上為自動化回測與簡單訊號判定，僅供參考。\n")
    return "\n".join(md)

def create_notion_page(title, markdown_content):
    if not NOTION_TOKEN or not NOTION_PARENT_PAGE_ID:
        print("Notion token or parent page id not set; skip Notion upload.")
        return None
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json"
    }
    payload = {
        "parent": { "page_id": NOTION_PARENT_PAGE_ID },
        "properties": {
            "title": [
                {
                    "type": "text",
                    "text": {"content": title}
                }
            ]
        },
        "children": [
            {
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [
                        {"type": "text", "text": {"content": markdown_content}}
                    ],
                    "language": "markdown"
                }
            }
        ]
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload))
    if r.status_code in (200,201):
        print("Notion page created.")
        return r.json()
    else:
        print("Notion API error:", r.status_code, r.text)
        return None

def main():
    results = {}
    for name, ticker in TICKERS.items():
        try:
            df = fetch_df(ticker)
            if df.shape[0] < 30:
                print(f"{ticker} 資料不足")
                results[name] = {"best": None, "signal": "資料不足"}
                continue
            best = pick_best_strategy(df)
            sig = today_signal(df, best)
            results[name] = {"best": best, "signal": sig}
        except Exception as e:
            print("Error for", ticker, e)
            results[name] = {"best": None, "signal": "錯誤"}

    md = make_markdown(results)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(md)
    # Create Notion page
    title = f"每日策略報告 {TODAY.isoformat()}"
    create_notion_page(title, md)
    print("Report generated:", REPORT_FILE)

if __name__ == "__main__":
    main()
