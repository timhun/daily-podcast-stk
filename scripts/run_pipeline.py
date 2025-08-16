import os
import json
import pandas as pd
from datetime import datetime
from scripts.fetch_market_data import fetch_market_data
from scripts.quantity_strategy_0050 import run_backtest

def generate_podcast_script():
    # 讀取市場數據
    daily_df = pd.read_csv('data/daily.csv', parse_dates=['Date'])
    hourly_df = pd.read_csv('data/hourly.csv', parse_dates=['Date'])
    
    # 提取最新數據
    twii = daily_df[daily_df['Symbol'] == '^TWII'].iloc[-1]
    twii_prev = daily_df[daily_df['Symbol'] == '^TWII'].iloc[-2]
    twii_change = twii['Close'] - twii_prev['Close']
    twii_pct = (twii_change / twii_prev['Close']) * 100
    
    ts_0050 = daily_df[daily_df['Symbol'] == '0050.TW'].iloc[-1]
    ts_0050_prev = daily_df[daily_df['Symbol'] == '0050.TW'].iloc[-2]
    ts_0050_pct = ((ts_0050['Close'] - ts_0050_prev['Close']) / ts_0050_prev['Close']) * 100
    
    ts_2330 = daily_df[daily_df['Symbol'] == '2330.TW'].iloc[-1]
    ts_2330_prev = daily_df[daily_df['Symbol'] == '2330.TW'].iloc[-2]
    ts_2330_pct = ((ts_2330['Close'] - ts_2330_prev['Close']) / ts_2330_prev['Close']) * 100
    
    ts_0050_hourly = hourly_df[hourly_df['Symbol'] == '0050.TW'].iloc[-1]
    
    # 假設外資期貨數據
    futures_net = "淨空 34,207 口，較前日減少 172 口（假設數據）"
    
    # 讀取量價策略輸出
    with open('data/daily_sim.json', 'r', encoding='utf-8') as f:
        daily_sim = json.load(f)
    with open('data/backtest_report.json', 'r', encoding='utf-8') as f:
        backtest = json.load(f)
    with open('data/strategy_history.json', 'r', encoding='utf-8') as f:
        history = '\n'.join([f"{h['date']}: signal {h['strategy']['signal']}, sharpe {h['sharpe']}, mdd {h['mdd']}" for h in json.load(f)])
    
    market_data = f"""
    - TAIEX (^TWII): 收盤 {twii['Close']:.2f} 點，漲跌 {twii_change:.2f} 點 ({twii_pct:.2f}%)，成交量 {twii['Volume']:,} 股
    - 0050.TW: 收盤 {ts_0050['Close']:.2f} 元，漲跌 {ts_0050_pct:.2f}%，成交量 {ts_0050['Volume']:,} 股
    - 2330.TW: 收盤 {ts_2330['Close']:.2f} 元，漲跌 {ts_2330_pct:.2f}%，成交量 {ts_2330['Volume']:,} 股
    - 0050.TW 小時線: 最新價格 {ts_0050_hourly['Close']:.2f} 元，成交量 {ts_0050_hourly['Volume']:,} 股
    - 外資期貨未平倉水位: {futures_net}
    """
    
    # 讀取 prompt 並生成播報
    with open('prompt/tw.txt', 'r', encoding='utf-8') as f:
        prompt = f.read()
    
    prompt = prompt.format(
        current_date=datetime.now().strftime('%Y-%m-%d'),
        market_data=market_data,
        SIG=daily_sim['signal'],
        PRICE=daily_sim['price'],
        VOLUME_RATE=daily_sim['volume_rate'],
        SIZE=daily_sim['size_pct'],
        OOS_SHARPE=backtest['metrics']['sharpe_ratio'],
        OOS_MDD=backtest['metrics']['max_drawdown'],
        LATEST_HISTORY=history
    )
    
    # 儲存播報
    os.makedirs('data', exist_ok=True)
    with open('data/podcast_script.txt', 'w', encoding='utf-8') as f:
        f.write(prompt)

def main():
    mode = os.environ.get('MODE', 'hourly')
    print(f"運行模式: {mode}")
    
    # 抓取市場數據
    fetch_market_data()
    
    # 運行回測
    run_backtest()
    
    # 生成播報腳本
    generate_podcast_script()
    print("播報腳本已儲存至 data/podcast_script.txt")

if __name__ == '__main__':
    main()