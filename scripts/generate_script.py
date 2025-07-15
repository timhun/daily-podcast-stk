from datetime import datetime
from fetch_data import fetch_indices, fetch_crypto, fetch_gold, fetch_top_stocks, fetch_news

def generate_podcast_script():
    indices = fetch_indices()
    btc = fetch_crypto()
    gold = fetch_gold()
    stocks = fetch_top_stocks()
    news = fetch_news()
    date = datetime.now().strftime('%Y年%m月%d日')

    script = f"""
    《大叔說財經科技投資》 - {date}
    開場白
    大家好！我是大叔，歡迎來到《大叔說財經科技投資》！今天是{date}，我們將盤點昨日市場動態...

    (1) 美股四大指數
    道瓊指數收盤 {indices['^DJI']['close']} 點，漲跌幅 {indices['^DJI']['change']}%...
    納斯達克指數收盤 {indices['^IXIC']['close']} 點，漲跌幅 {indices['^IXIC']['change']}%...

    (2) QQQ與SPY ETF
    QQQ收盤 {indices['QQQ']['close']}，漲跌幅 {indices['QQQ']['change']}%...
    SPY收盤 {indices['SPY']['close']}，漲跌幅 {indices['SPY']['change']}%...

    (3) 比特幣與黃金期貨
    比特幣收盤 ${btc['price']}，漲跌幅 {btc['change']}%...
    黃金期貨收盤 ${gold['price']}，漲跌幅 {gold['change']}%...

    (4) Top 5熱門股
    昨日熱門股包括 {', '.join(stocks)}...

    (5) AI新聞
    {news['ai']['title']}：{news['ai']['summary']}...

    (6) 總體經濟新聞
    {news['economic']['title']}：{news['economic']['summary']}...

    (7) 每日投資金句
    “Only buy something that you’d be perfectly happy to hold if the market shut down for 10 years.” - Warren Buffett

    結語
    今天的節目到此結束！請持續鎖定我們，明天見！
    """
    with open('script.txt', 'w', encoding='utf-8') as f:
        f.write(script)
    return script
