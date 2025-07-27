import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import time
import json
import re
import pytz
from bs4 import BeautifulSoup

TW_TZ = pytz.timezone("Asia/Taipei")

# ======== 資料抓取函數區 ========

def get_twse_index_data(date):
    try:
        url = f"https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX?date={date}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
        for item in data:
            if item[1] == '發行量加權股價指數':
                return pd.DataFrame([{
                    'Date': pd.to_datetime(date),
                    'Close': float(item[2].replace(",", ""))
                }])
    except Exception as e:
        print(f"⚠️ 加權指數資料擷取失敗：{e}")
    return None

def get_twse_volume_data(date):
    try:
        url = f"https://www.twse.com.tw/exchangeReport/FMTQIK?response=json&date={date}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            return None
        tw_year = int(date[:4]) - 1911
        roc_date = f"{tw_year}/{date[4:6]}/{date[6:8]}"
        for row in data:
            if row[0] == roc_date:
                return pd.DataFrame([{
                    'Date': pd.to_datetime(date),
                    'Volume': float(row[2].replace(",", "")),
                    'VolumeBillion': float(row[1].replace(",", "")) / 1e8
                }])
    except Exception as e:
        print(f"⚠️ 成交量擷取失敗：{e}")
    return None

def get_twse_taiwan_foreign_buy(date):
    try:
        url = f"https://www.twse.com.tw/fund/TWIIIAI?response=csv&date={date}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        lines = r.text.splitlines()
        for line in lines:
            if line.startswith('"1"'):
                parts = line.replace('"', '').split(',')
                foreign = float(parts[1]) - float(parts[2])
                investment = float(parts[4]) - float(parts[5])
                dealer = float(parts[7]) - float(parts[8])
                total = foreign + investment + dealer
                return pd.DataFrame([{
                    'Date': pd.to_datetime(date),
                    'ForeignBuy': foreign / 1e8,
                    'Investment': investment / 1e8,
                    'Dealer': dealer / 1e8,
                    'TotalNetBuy': total / 1e8
                }])
    except Exception as e:
        print(f"⚠️ 法人買賣超擷取失敗：{e}")
    return None

def get_latest_taiex_summary():
    end_date = datetime.now(TW_TZ)
    start_date = end_date - timedelta(days=60)

    index_data = []
    volume_data = []
    foreign_data = []

    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y%m%d")

        idx = get_twse_index_data(date_str)
        if idx is not None:
            index_data.append(idx)

        vol = get_twse_volume_data(date_str)
        if vol is not None:
            volume_data.append(vol)

        foreign = get_twse_taiwan_foreign_buy(date_str)
        if foreign is not None:
            foreign_data.append(foreign)

        current += timedelta(days=1)
        time.sleep(0.3)

    if not index_data or not volume_data:
        return None

    df = pd.concat(index_data).merge(
        pd.concat(volume_data), on="Date", how="inner"
    )

    if foreign_data:
        df = df.merge(pd.concat(foreign_data), on="Date", how="left")

    df.sort_values("Date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    df["Change"] = df["Close"].diff()
    df["ChangePct"] = df["Close"].pct_change() * 100
    return df

# ======== 技術指標 ========

def calculate_ma(df, window):
    return df['Close'].rolling(window=window).mean()

def calculate_ema(df, span):
    return df['Close'].ewm(span=span, adjust=False).mean()

def calculate_macd_advanced(df):
    ema12 = calculate_ema(df, 12)
    ema26 = calculate_ema(df, 26)
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def calculate_dynamic_volume_threshold(df, window=20):
    return df['Volume'].rolling(window=window).mean() + df['Volume'].rolling(window=window).std()

def calculate_foreign_buy_sum(df, window=5):
    return df['ForeignBuy'].rolling(window=window).sum()

def score_signal(row, ma5, ma10, ma20, macd, signal, fsum, vol_thres):
    score = 0
    if row['Close'] > ma5:
        score += 1
    if row['Close'] > ma10:
        score += 1.5
    if row['Close'] > ma20:
        score += 2
    if macd > signal and macd > 0:
        score += 1
    if fsum > 0:
        score += 1
    if row['Volume'] > vol_thres:
        score += 1
    return score

def analyze_bang_bang_line(row, df):
    df['MA5'] = calculate_ma(df, 5)
    df['MA10'] = calculate_ma(df, 10)
    df['MA20'] = calculate_ma(df, 20)
    df['MACD'], df['Signal'] = calculate_macd_advanced(df)
    df['VolThreshold'] = calculate_dynamic_volume_threshold(df)
    df['ForeignBuySum5'] = calculate_foreign_buy_sum(df)

    r = df[df["Date"] == row["Date"]].iloc[0]

    score = score_signal(
        r, r['MA5'], r['MA10'], r['MA20'], r['MACD'], r['Signal'], r['ForeignBuySum5'], r['VolThreshold']
    )

    if score >= 6:
        trend = "Strong Bull"
        suggestion = "📈 市場呈現強烈多頭，建議加倉 0050 或 00631L。"
    elif score >= 5:
        trend = "Weak Bull"
        suggestion = "📈 市場偏多，可考慮適度加倉。"
    elif score <= 2:
        trend = "Bear"
        suggestion = "📉 市場偏空，建議減碼或觀望。"
    elif score <= 3:
        trend = "Weak Bear"
        suggestion = "📉 市場震盪偏弱，建議保守操作。"
    else:
        trend = "Neutral"
        suggestion = "📊 市場整理中，建議觀望。"

    lines = [
        f"📊 分析日期：{r['Date'].strftime('%Y%m%d')}",
        f"收盤：{r['Close']:,.2f}（漲跌：{r['Change']:+.2f}，{r['ChangePct']:+.2f}%）",
        f"成交金額：約 {r['VolumeBillion']:.0f} 億元",
        f"均線：5日 {r['MA5']:.2f}｜10日 {r['MA10']:.2f}｜20日 {r['MA20']:.2f}",
        f"MACD 值：{r['MACD']:+.2f}",
        f"幫幫忙大盤線分數：{score:.1f}（趨勢：{trend}）",
        suggestion
    ]

    if pd.notna(r.get("ForeignBuy")):
        lines.append(
            f"📥 法人買賣超（億）：外資 {r['ForeignBuy']:+.1f}，投信 {r['Investment']:+.1f}，自營商 {r['Dealer']:+.1f}，合計 {r['TotalNetBuy']:+.1f}"
        )

    return "\n".join(lines)

# ======== 主程式 ========

if __name__ == "__main__":
    now_tw = datetime.now(TW_TZ)
    if now_tw.weekday() in [5, 6]:  # 週六週日
        print("⛱️ 週末假期，跳過大盤多空分析。")
        exit(0)

    df = get_latest_taiex_summary()
    if df is None or df.empty:
        print("❌ 無法取得加權指數資料")
        exit(1)

    row = df.iloc[-1]
    try:
        summary = analyze_bang_bang_line(row, df)
    except Exception as e:
        print(f"⚠️ 分析失敗：{e}")
        summary = "⚠️ 資料不完整，無法判斷多空。"

    print(summary)

    output_dir = "docs/podcast"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "bullish_signal_tw.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"✅ 已儲存多空判斷至：{output_path}")
