# generate_script.py
import pandas as pd
import os
from datetime import datetime
import argparse
from grok_api import optimize_script_with_grok
from config import US_TICKERS, TW_TICKERS, US_MARKET_NAMES, TW_MARKET_NAMES, DATA_DIR, DOCS_DIR

def generate_podcast_summary(tickers, market_names, session, output_dir, output_file, is_us=True):
    latest_data = {}
    for ticker in tickers:
        csv_file = os.path.join(DATA_DIR, f'{ticker.replace("^", "")}.csv')
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file, parse_dates=['Date'])
            df['Date'] = pd.to_datetime(df['Date'])
            latest_row = df.iloc[-1]
            amount_twd = (latest_row['Close'] * latest_row['Volume']) / 1e8
            latest_data[ticker] = {
                'Date': latest_row['Date'].strftime('%Y-%m-%d'),
                'Close': latest_row['Close'],
                'Volume': latest_row['Volume'],
                'Amount': amount_twd
            }
        else:
            print(f'找不到 {ticker}.csv，跳過')

    current_date = datetime.now()
    initial_script = f"錄音日期：{current_date.strftime('%Y年%m月%d日')}\n\n"
    if is_us:
        initial_script += (
            "大家好，我是幫幫忙，歡迎收聽《幫幫忙說美股》。今天是2025年8月10日，我們將從最新市場數據出發，"
            "深入探討美股走勢、ETF交易策略、比特幣趨勢，以及原油與美國公債利率的動態，並聚焦AI投資機會和台股融資變化，"
            "為您提供專業的財經洞察。\n\n"
            f"### 一、美股指數：弱勢震盪背後的影響因素\n\n"
            f"根據最新數據，截至8月8日，納斯達克指數（^IXIC）收盤報21,450.02點，上漲207.32點，漲幅0.98%，"
            f"成交金額約{latest_data.get('^IXIC', {}).get('Amount', 0):,.2f}億元；"
            f"標普500指數（^GSPC）收盤報6,389.45點，上漲49.45點，漲幅0.78%，"
            f"成交金額約{latest_data.get('^GSPC', {}).get('Amount', 0):,.2f}億元。\n\n"
            # ... 其他美股內容（簡略）
            f"### 八、投資金句\n\n"
            "引用Andre Kostolany：『耐心是投資的關鍵，市場總會回報那些懂得等待的人。』\n\n"
            "我是幫幫忙，感謝收聽《幫幫忙說美股》，明天同一時間再會！"
        )
    else:
        initial_script += (
            "大家好，我是幫幫忙，歡迎收聽《幫幫忙說台股》。今天是2025年8月10日，"
            "我們將從最新台股市場數據出發，結合全球財經動態，深入分析台股走勢、ETF表現，"
            "以及關鍵影響因素，為您提供專業的市場洞察。\n\n"
            f"### 一、台股指數：穩中求進的動能\n\n"
            f"台股加權指數（^TWII）8月8日收盤報24,021.26點，上漲17.49點，漲幅0.07%，"
            f"成交金額{latest_data.get('^TWII', {}).get('Amount', 0):,.2f}億元。\n\n"
            # ... 其他台股內容（簡略）
            f"### 八、投資金句\n\n"
            "引用Andre Kostolany：『投資就像種樹，今天播種，明天才能乘涼。』\n\n"
            "我是幫幫忙，感謝收聽《幫幫忙說台股》，明天再見！"
        )

    api_key = os.getenv("XAI_API_KEY")
    if api_key:
        optimized_script = optimize_script_with_grok(initial_script, api_key)
    else:
        print("未找到 XAI_API_KEY，使用初始逐字稿")
        optimized_script = initial_script

    os.makedirs(output_dir, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(optimized_script)
    print(f"{session} 逐字稿已儲存至 {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate podcast scripts")
    parser.add_argument('--us', action='store_true', help="Generate US market script")
    parser.add_argument('--tw', action='store_true', help="Generate TW market script")
    args = parser.parse_args()

    date_str = datetime.now().strftime('%Y%m%d')
    if args.us:
        generate_podcast_summary(
            tickers=US_TICKERS,
            market_names=US_MARKET_NAMES,
            session="早上6點 - 美國股市",
            output_dir=os.path.join(DOCS_DIR, f'{date_str}_us'),
            output_file=os.path.join(DOCS_DIR, f'{date_str}_us/podcast_{date_str}_us.txt'),
            is_us=True
        )
    if args.tw:
        generate_podcast_summary(
            tickers=TW_TICKERS,
            market_names=TW_MARKET_NAMES,
            session="下午2點 - 台股",
            output_dir=os.path.join(DOCS_DIR, f'{date_str}_tw'),
            output_file=os.path.join(DOCS_DIR, f'{date_str}_tw/podcast_{date_str}_tw.txt'),
            is_us=False
        )