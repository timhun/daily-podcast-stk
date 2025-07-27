import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import re

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
                    'Volume': float(row[2].replace(',', ''))
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
            if '"買進金額"' in line or len(line.split(',')) < 1:
                continue
            row = line.replace('"', '').split(',')
            if row[0] == '1':
                net_buy = float(row[1].replace(',', '')) - float(row[2].replace(',', ''))
                data.append({
                    'Date': date,
                    'ForeignBuy': net_buy / 100000000  # 轉為億
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
        
        # 假設數據嵌入在JSON中（需檢查實際結構）
        match = re.search(r'root\.App\.main = ({.*?});', response.text, re.DOTALL)
        if not match:
            raise ValueError("無法提取Yahoo Finance JSON數據")
        
        json_data = json.loads(match.group(1))
        # 模擬數據，實際需解析JSON
        data = [
            {'Date': '2025/07/25', 'ForeignBuy': 73.61},
            {'Date': '2025/07/24', 'ForeignBuy': 101.53},
            {'Date': '2025/07/23', 'ForeignBuy': 84.32},
            # 需替換為實際解析結果
        ]
        
        df = pd.DataFrame(data)
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
        
        # 假設數據嵌入在表格或JSON中（需檢查實際結構）
        # 此處模擬數據，實際需解析HTML或API
        data = [
            {'Date': '2025/07/25', 'ForeignBuy': 73.61},
            {'Date': '2025/07/24', 'ForeignBuy': 101.53},
            {'Date': '2025/07/23', 'ForeignBuy': 84.32},
            # 需替換為實際解析結果
        ]
        
        df = pd.DataFrame(data)
        df['Date'] = pd.to_datetime(df['Date'])
        df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
        return df.sort_values('Date').reset_index(drop=True)
    except Exception as e:
        print(f"玩股網外資買賣超取得失敗: {e}")
        return None

def get_combined_data(start_date, end_date):
    """整合數據，優先TWSE，備案Yahoo或Wantgoo"""
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
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
        
        # 優先TWSE外資數據
        foreign_df = get_twse_taiwan_foreign_buy(date_str)
        if foreign_df is None:
            # 備案1：Yahoo Finance
            foreign_df = get_yahoo_foreign_buy(start_date, end_date)
            if foreign_df is None:
                # 備案2：玩股網
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
        return result
    return None

# 幫幫忙大盤線
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

def calculate_volume_avg(df, window=60):
    return df['Volume'].rolling(window=window).mean()

def calculate_dynamic_volume_threshold(df, window=60):
    vol_std = df['Volume'].rolling(window=window).std()
    vol_avg = df['Volume'].rolling(window=window).mean()
    return vol_avg + vol_std

def calculate_foreign_buy_sum(df, window=5):
    return df['ForeignBuy'].rolling(window=window).sum()

def score_signal(row, ma10, ma20, ma60, macd, signal, foreign_buy_sum, vol_threshold):
    score = 0
    if row['Close'] > ma10:
        score += 1
    if row['Close'] > ma20:
        score += 1.5
    if row['Close'] > ma60:
        score += 2
    if macd > signal and macd > 0:
        score += 1
    if foreign_buy_sum > 0:
        score += 1
    if row['Volume'] > vol_threshold:
        score += 1
    return score

def calculate_bang_bang_line(df):
    df['MA10'] = calculate_ma(df, 10)
    df['MA20'] = calculate_ma(df, 20)
    df['MA60'] = calculate_ma(df, 60)
    df['MACD'], df['Signal'] = calculate_macd_advanced(df)
    df['VolThreshold'] = calculate_dynamic_volume_threshold(df, 60)
    df['ForeignBuySum5'] = calculate_foreign_buy_sum(df, 5)

    scores = []
    for idx, row in df.iterrows():
        score = score_signal(
            row,
            row['MA10'], row['MA20'], row['MA60'],
            row['MACD'], row['Signal'], row['ForeignBuySum5'], row['VolThreshold']
        )
        scores.append(score)
    df['Score'] = scores

    conditions = [
        (df['Score'] >= 6),
        (df['Score'] >= 5),
        (df['Score'] <= 2),
        (df['Score'] <= 3)
    ]
    choices = ['Strong Bull', 'Weak Bull', 'Bear', 'Weak Bear']
    df['Trend'] = np.select(conditions, choices, default='Neutral')

    df['SustainedTrend'] = df['Trend'].rolling(window=3).apply(
        lambda x: 'Sustained Bull' if all(x.isin(['Strong Bull', 'Weak Bull'])) else 'Sustained Bear' if all(x.isin(['Bear', 'Weak Bear'])) else 'None', raw=False
    )

    return df

# 主程式
if __name__ == "__main__":
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d')

    data = get_combined_data(start_date, end_date)
    
    if data is not None:
        data.to_csv('market_data.csv', index=False)
        
        df = pd.read_csv('market_data.csv', parse_dates=['Date'])
        df = df.sort_values('Date').reset_index(drop=True)
        df_result = calculate_bang_bang_line(df)
        print("幫幫忙大盤線結果：")
        print(df_result[['Date', 'Close', 'Score', 'Trend', 'SustainedTrend']].tail(20))
