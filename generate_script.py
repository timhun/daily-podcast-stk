# generate_script.py
import pandas as pd
import os
from datetime import datetime
import argparse
from grok_api import optimize_script_with_grok
from config import US_TICKERS, TW_TICKERS, US_MARKET_NAMES, TW_MARKET_NAMES, DATA_DIR, DOCS_DIR

USD_TO_TWD = 32

def generate_podcast_summary(tickers, market_names, session, output_dir, output_file, is_us=True):
    latest_data = {}
    for ticker in tickers:
        csv_file = os.path.join(DATA_DIR, f'{ticker.replace("^", "")}.csv')
        if os.path.exists(csv_file):
            try:
                df = pd.read_csv(csv_file, parse_dates=['Date'])
                df['Date'] = pd.to_datetime(df['Date'])
                latest_row = df.iloc[-1]
                latest_date = latest_row['Date'].strftime('%Y-%m-%d')
                print(f'{ticker} 使用資料日期：{latest_date}')
                amount_twd = (latest_row['Close'] * latest_row['Volume'] * USD_TO_TWD) / 1e8 if is_us else (latest_row['Close'] * latest_row['Volume']) / 1e8
                latest_data[ticker] = {
                    'Date': latest_date,
                    'Close': latest_row['Close'],
                    'Volume': latest_row['Volume'],
                    'Amount': amount_twd
                }
            except Exception as e:
                print(f'讀取 {ticker} CSV 失敗：{e}')
        else:
            print(f'找不到 {ticker}.csv，跳過')

    if not latest_data:
        print(f'無有效資料可用，無法生成 {session} 逐字稿')
        return

    current_date = datetime.now()
    initial_script = f"錄音日期：{current_date.strftime('%Y年%m月%d日')}\n\n"
    if is_us:
        initial_script += (
            "大家好，我是幫幫忙，歡迎收聽《幫幫忙說美股》。今天是2025年8月11日，我們將從最新市場數據出發，"
            "深入探討美股走勢、ETF交易策略、比特幣趨勢、黃金期貨動態，以及AI投資機會和台股融資變化，"
            "為您提供專業的財經洞察。\n\n"
            f"### 一、美股指數：弱勢震盪背後的影響因素\n\n"
            f"根據最新數據，截至{latest_data.get('^IXIC', {}).get('Date', '未知日期')}，"
            f"納斯達克指數（^IXIC）收盤報{latest_data.get('^IXIC', {}).get('Close', 0):,.2f}點，"
            f"成交金額約{latest_data.get('^IXIC', {}).get('Amount', 0):,.2f}億元；"
            f"標普500指數（^GSPC）收盤報{latest_data.get('^GSPC', {}).get('Close', 0):,.2f}點，"
            f"成交金額約{latest_data.get('^GSPC', {}).get('Amount', 0):,.2f}億元。\n\n"
            "影響因素包括：Fed降息預期升溫，9月可能降息50個基點；"
            "Trump關稅政策影響科技和消費品板塊。\n\n"
            f"### 二、ETF與黃金期貨\n\n"
            f"QQQ收盤報{latest_data.get('QQQ', {}).get('Close', 0):,.2f}點，"
            f"成交金額{latest_data.get('QQQ', {}).get('Amount', 0):,.2f}億元；"
            f"SPY收盤報{latest_data.get('SPY', {}).get('Close', 0):,.2f}點，"
            f"成交金額{latest_data.get('SPY', {}).get('Amount', 0):,.2f}億元；"
            f"黃金期貨（GC=F）收盤報{latest_data.get('GC=F', {}).get('Close', 0):,.2f}美元，"
            f"成交金額{latest_data.get('GC=F', {}).get('Amount', 0):,.2f}億元。\n\n"
            f"### 三、比特幣趨勢\n\n"
            f"比特幣（BTC-USD）收盤報{latest_data.get('BTC-USD', {}).get('Close', 0):,.2f}美元，"
            f"成交金額{latest_data.get('BTC-USD', {}).get('Amount', 0):,.2f}億元。\n\n"
            f"### 四、投資金句\n\n"
            "引用Andre Kostolany：『耐心是投資的關鍵，市場總會回報那些懂得等待的人。』\n\n"
            "我是幫幫忙，感謝收聽《幫幫忙說美股》，明天再會！"
        )
    else:
        initial_script += (
            "大家好，我是幫幫忙，歡迎收聽《幫幫幫說台股》。今天是2025年8月11日，"
            "我們將從最新台股市場數據出發，結合全球財經動態，深入分析台股走勢。\n\n"
            f"### 一、台股指數\n\n"
            f"台股加權指數（^TWII）{latest_data.get('^TWII', {}).get('Date', '未知日期')}收盤報"
            f"{latest_data.get('^TWII', {}).get('Close', 0):,.2f}點，"
            f"成交金額{latest_data.get('^TWII', {}).get('Amount', 0):,.2f}億元。\n\n"
            f"### 二、ETF與台積電\n\n"
            f"元大台灣50（0050.TW）收盤報{latest_data.get('0050.TW', {}).get('Close', 0):,.2f}點，"
            f"成交金額{latest_data.get('0050.TW', {}).get('Amount', 0):,.2f}億元；"
            f"台積電（2330.TW）收盤報{latest_data.get('2330.TW', {}).get('Close', 0):,.2f}點，"
            f"成交金額{latest_data.get('2330.TW', {}).get('Amount', 0):,.2f}億元。\n\n"
            f"### 三、投資金句\n\n"
            "引用Andre Kostolany：『投資就像種樹，今天播種，明天才能乘涼。』\n\n"
            "我是幫幫忙，感謝收聽《幫幫忙說台股》，明天再見！"
        )

    api_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
    if api_key:
        optimized_script = optimize_script_with_grok(initial_script, api_key)
    else:
        print("未找到 GROK_API_KEY/XAI_API_KEY，使用初始逐字稿")
        optimized_script = initial_script

    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(optimized_script)
        print(f"{session} 逐字稿已儲存至 {output_file}")
    except Exception as e:
        print(f"儲存 {session} 逐字稿失敗：{e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate podcast scripts")
    parser.add_argument('--us', action='store_true', help="Generate US market script")
    parser.add_argument('--tw', action='store_true', help="Generate TW market script")
    args = parser.parse_args()

    date_str = datetime.now().strftime('%Y%m%d')
    if args.us:
        output_dir = os.path.abspath(os.path.join(DOCS_DIR, f'{date_str}_us'))
        output_file = os.path.abspath(os.path.join(output_dir, f'podcast_{date_str}_us.txt'))
        generate_podcast_summary(
            tickers=US_TICKERS,
            market_names=US_MARKET_NAMES,
            session="早上6點 - 美國股市",
            output_dir=output_dir,
            output_file=output_file,
            is_us=True
        )
    if args.tw:
        output_dir = os.path.abspath(os.path.join(DOCS_DIR, f'{date_str}_tw'))
        output_file = os.path.abspath(os.path.join(output_dir, f'podcast_{date_str}_tw.txt'))
        generate_podcast_summary(
            tickers=TW_TICKERS,
            market_names=TW_MARKET_NAMES,
            session="下午2點 - 台股",
            output_dir=output_dir,
            output_file=output_file,
            is_us=False
        )