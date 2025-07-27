#analyze_bullish_signal_tw_dev.py
import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import re
from bs4 import BeautifulSoup

# 台北時區
from datetime import timezone
TW_TZ = timezone(timedelta(hours=8))

# TWSE Open API數據抓取
def get_twse_index_data(date):
    """從TWSE Open API取得大盤收盤價（Close）"""
    try:
        url = f"https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX?date={date}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()['data']
        for item in data:
            if item[1] == '發行量加權股價指數':
                return pd.DataFrame([{
                    'Date': date,
                    'Close': float(item[2].replace(',', ''))
                }])
        return None
    except Exception as e:
        print(f"日期 {date} 指數數據取得失敗: {e}")
        return None

def get_twse_volume_data(date):
    """從TWSE網站取得大盤成交量（Volume）"""
    try:
        url = f"https://www.twse.com.tw/exchangeReport/FMTQIK?response=json&date={date}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        if 'data' not in data:
            return None
        
        tw_year = int(date[:4]) - 1911
        target_date = f"{tw_year}/{date[4:6]}/{date[6:8]}"
        for row in data['data']:
            if row[0] == target_date:
                return pd.DataFrame([{
                    'Date': date,
                    'Volume': float(row[2].replace(',', '')),
                    'VolumeBillion': float(row[1].replace(',', '')) / 100000000  # 成交金額（億元）
                }])
        return None
    except Exception as e:
        print(f"日期 {date} 成交量數據取得失敗: {e}")
        return None

def get_twse_taiwan_foreign_buy(date):
    """從TWSE網站取得大盤外資買賣超（ForeignBuy）"""
    try:
        url = f"https://www.twse.com.tw/fund/TWIIIAI?response=csv&date={date}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        data = []
        for line in lines:
            if '"買進金額"' in line or len(line.split(',')) < 3:
                continue
            row = line.replace('"', '').split(',')
            if row[0] == '1':
                net_buy = float(row[1].replace(',', '')) - float(row[2].replace(',', ''))
                data.append({
                    'Date': date,
                    'ForeignBuy': net_buy / 100000000,  # 轉為億
                    'Investment': float(row[4].replace(',', '')) / 100000000,  # 投信
                    'Dealer': float(row[7].replace(',', '')) / 100000000,  # 自營商
                    'TotalNetBuy': (float(row[1].replace(',', '')) + float(row[4].replace(',', '')) + float(row[7].replace(',', '')) - 
                                    float(row[2].replace(',', '')) - float(row[5].replace(',', '')) - float(row[8].replace(',', ''))) / 100000000
                })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
        return df
    except Exception as e:
        print(f"日期 {date} 大盤外資買賣超取得失敗: {e}")
        return None

def get_yahoo_foreign_buy(start_date, end_date):
    """從Yahoo Finance抓取大盤外資買賣超（備案1）"""
    try:
        url = "https://tw.stock.yahoo.com/institutional-trading/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # 假設數據在表格中，需檢查實際結構
        table = soup.find('table', class_='table')
        if not table:
            raise ValueError("無法找到Yahoo Finance表格")
        
        data = []
        rows = table.find_all('tr')[1:]  # 跳過表頭
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 4:
                date = pd.to_datetime(cols[0].text.strip())
                if start_date <= date <= end_date:
                    foreign = float(cols[1].text.strip().replace(',', ''))
                    investment = float(cols[2].text.strip().replace(',', ''))
                    dealer = float(cols[3].text.strip().replace(',', ''))
                    total_netbuy = foreign + investment + dealer
                    data.append({
                        'Date': date,
                        'ForeignBuy': foreign,
                        'Investment': investment,
                        'Dealer': dealer,
                        'TotalNetBuy': total_netbuy
                    })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
        return df.sort_values('Date').reset_index(drop=True)
    except Exception as e:
        print(f"Yahoo Finance外資買賣超取得失敗: {e}")
        return None

def get_wantgoo_foreign_buy(start_date, end_date):
    """從玩股網抓取大盤外資買賣超（備案2）"""
    try:
        url = "https://www.wantgoo.com/stock/institutional-investors/three-trade-for-trading-amount"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # 假設數據在表格中，需檢查實際結構
        table = soup.find('table', class_='table')
        if not table:
            raise ValueError("無法找到玩股網表格")
        
        data = []
        rows = table.find_all('tr')[1:]  # 跳過表頭
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 4:
                date = pd.to_datetime(cols[0].text.strip())
                if start_date <= date <= end_date:
                    foreign = float(cols[1].text.strip().replace(',', ''))
                    investment = float(cols[2].text.strip().replace(',', ''))
                    dealer = float(cols[3].text.strip().replace(',', ''))
                    total_netbuy = foreign + investment + dealer
                    data.append({
                        'Date': date,
                        'ForeignBuy': foreign,
                        'Investment': investment,
                        'Dealer': dealer,
                        'TotalNetBuy': total_netbuy
                    })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
        return df.sort_values('Date').reset_index(drop=True)
    except Exception as e:
        print(f"玩股網外資買賣超取得失敗: {e}")
        return None

def get_latest_taiex_summary():
    """取代原始get_latest_taiex_summary，取得歷史數據"""
    end_date = datetime.today()
    start_date = end_date - timedelta(days=60)  # 取60天數據以計算短期均線和MACD
    
    index_data = []
    volume_data = []
    foreign_data = []
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        
        index_df = get_twse_index_data(date_str)
        if index_df is not None:
            index_data.append(index_df)
        
        volume_df = get_twse_volume_data(date_str)
        if volume_df is not None:
            volume_data.append(volume_df)
        
        foreign_df = get_twse_taiwan_foreign_buy(date_str)
        if foreign_df is None:
            foreign_df = get_yahoo_foreign_buy(start_date, end_date)
            if foreign_df is None:
                foreign_df = get_wantgoo_foreign_buy(start_date, end_date)
        if foreign_df is not None:
            foreign_data.append(foreign_df)
        
        current_date += timedelta(days=1)
        time.sleep(1)
    
    result = None
    if index_data:
        index_df = pd.concat(index_data).reset_index(drop=True)
        index_df['Date'] = pd.to_datetime(index_df['Date'])
        result = index_df
    
    if volume_data:
        volume_df = pd.concat(volume_data).reset_index(drop=True)
        volume_df['Date'] = pd.to_datetime(volume_df['Date'])
        result = pd.merge(result, volume_df, on='Date', how='inner') if result is not None else volume_df
    
    if foreign_data:
        foreign_df = pd.concat(foreign_data).reset_index(drop=True)
        foreign_df['Date'] = pd.to_datetime(foreign_df['Date'])
        result = pd.merge(result, foreign_df, on='Date', how='inner') if result is not None else foreign_df
    
    if result is not None:
        if result[['Close', 'Volume', 'ForeignBuy']].isnull().any().any():
            print("警告：合併數據存在缺失值")
        result = result.sort_values('Date').reset_index(drop=True)
        
        # 計算漲跌與漲跌百分比
        result['Change'] = result['Close'].diff()
        result['ChangePct'] = result['Close'].pct_change() * 100
        
        return result
    return None

# 幫幫忙大盤線分析
def calculate_ma(df, window):
    return df['Close'].rolling(window=window).mean()

def calculate_ema(df, span):
    return df['Close'].ewm(span=span, adjust=False).mean()

def calculate_macd_advanced(df):
    ema_fast = calculate_ema(df, 12)
    ema_slow = calculate_ema(df, 26)
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def calculate_volume_avg(df, window=20):  # 改為20天以適應短線
    return df['Volume'].rolling(window=window).mean()

def calculate_dynamic_volume_threshold(df, window=20):
    vol_std = df['Volume'].rolling(window=window).std()
    vol_avg = df['Volume'].rolling(window=window).mean()
    return vol_avg + vol_std

def calculate_foreign_buy_sum(df, window=5):
    return df['ForeignBuy'].rolling(window=window).sum()

def score_signal(row, ma5, ma10, ma20, macd, signal, foreign_buy_sum, vol_threshold):
    score = 0
    if row['Close'] > ma5:
        score += 1
    if row['Close'] > ma10:
        score += 1.5
    if row['Close'] > ma20:
        score += 2
    if macd > signal and macd > 0:
        score += 1
    if foreign_buy_sum > 0:
        score += 1
    if row['Volume'] > vol_threshold:
        score += 1
    return score

def analyze_bang_bang_line(row, df):
    """融合幫幫忙大盤線的分析函數（短線版）"""
    # 計算短期均線
    df['MA5'] = calculate_ma(df, 5)
    df['MA10'] = calculate_ma(df, 10)
    df['MA20'] = calculate_ma(df, 20)
    df['MACD'], df['Signal'] = calculate_macd_advanced(df)
    df['VolThreshold'] = calculate_dynamic_volume_threshold(df, 20)
    df['ForeignBuySum5'] = calculate_foreign_buy_sum(df, 5)

    # 提取當前行的指標
    current_row = df[df['Date'] == row['Date']].iloc[0]
    close = current_row['Close']
    ma5 = current_row['MA5']
    ma10 = current_row['MA10']
    ma20 = current_row['MA20']
    macd = current_row['MACD']
    signal = current_row['Signal']
    volume_billion = current_row.get('VolumeBillion', None)
    change = current_row.get('Change', None)
    change_pct = current_row.get('ChangePct', None)
    foreign = current_row.get('ForeignBuy', None)
    investment = current_row.get('Investment', None)
    dealer = current_row.get('Dealer', None)
    total_netbuy = current_row.get('TotalNetBuy', None)
    date = current_row['Date']

    # 計算幫幫忙大盤線分數
    score = score_signal(current_row, ma5, ma10, ma20, macd, signal, 
                         current_row['ForeignBuySum5'], current_row['VolThreshold'])

    # 判斷趨勢
    if score >= 6:
        trend = 'Strong Bull'
        suggestion = '📈 市場呈現強烈多頭，建議加倉 0050 或 00631L。'
    elif score >= 5:
        trend = 'Weak Bull'
        suggestion = '📈 市場偏多，可考慮適度加倉 0050 或 00631L。'
    elif score <= 2:
        trend = 'Bear'
        suggestion = '📉 市場呈現空頭，建議減倉或觀望。'
    elif score <= 3:
        trend = 'Weak Bear'
        suggestion = '📉 市場偏空，建議謹慎操作。'
    else:
        trend = 'Neutral'
        suggestion = '📊 市場整理中，建議觀望。'

    # 檢查持續趨勢
    recent_trends = df.tail(3)['Score'].apply(
        lambda x: 'Bull' if x >= 5 else 'Bear' if x <= 3 else 'Neutral'
    )
    sustained_trend = 'Sustained Bull' if all(recent_trends.isin(['Bull'])) else \
                      'Sustained Bear' if all(recent_trends.isin(['Bear'])) else 'None'
    
    # 輸出格式
    lines = []
    lines.append(f"📊 分析日期：{date.strftime('%Y%m%d')}")
    lines.append(f"收盤：{close:,.2f}（漲跌：{change:+.2f}，{change_pct:+.2f}%）" if change is not None and change_pct is not None else f"收盤：{close:,.2f}")
    lines.append(f"成交金額：約 {volume_billion:.0f} 億元" if volume_billion else "成交金額：資料缺失")
    lines.append(f"均線：5日 {ma5:.2f}｜10日 {ma10:.2f}｜20日 {ma20:.2f}")
    lines.append(f"MACD 值：{macd:+.2f}")
    lines.append(f"幫幫忙大盤線分數：{score:.1f}（趨勢：{trend}）")
    if sustained_trend != 'None':
        lines.append(f"持續趨勢：{sustained_trend}")
    lines.append(suggestion)
    
    if all(x is not None for x in (foreign, investment, dealer, total_netbuy)):
        lines.append(f"📥 法人買賣超（億元）：外資 {foreign:+.1f}，投信 {investment:+.1f}，自營商 {dealer:+.1f}，合計 {total_netbuy:+.1f}")

    return "\n".join(lines)

# 主程式
if __name__ == "__main__":
    df = get_latest_taiex_summary()
    if df is None or df.empty:
        print("❌ 無法取得加權指數資料")
        exit(1)

    row = df.iloc[-1]  # 取最新一天
    try:
        summary = analyze_bang_bang_line(row, df)
    except Exception as e:
        print(f"⚠️ 分析失敗：{e}")
        summary = "⚠️ 資料不完整，無法判斷多空。"

    print(summary)

    # 儲存分析結果
    date_str = datetime.now(TW_TZ).strftime("%Y%m%d")
    output_dir = f"docs/podcast"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "bullish_signal_tw_dev.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"✅ 已儲存多空判斷至：{output_path}")
