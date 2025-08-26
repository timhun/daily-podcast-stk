import yfinance as yf
import requests
from bs4 import BeautifulSoup

def collect_data(mode):
    symbols = {'us': ['^GSPC', 'QQQ', 'NVDA'], 'tw': ['^TWII', '0050.TW', '2330.TW']}
    data = {}
    for symbol in symbols[mode]:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='1d')
        data[symbol] = {
            'close': hist['Close'].iloc[-1],
            'change': hist['Close'].pct_change().iloc[-1] * 100 if len(hist) > 1 else 0
        }

    # 簡單新聞抓取 (1 則)
    news_url = 'https://tw.stock.yahoo.com/rss?category=news' if mode == 'tw' else 'https://feeds.bloomberg.com/technology/news.rss'
    response = requests.get(news_url)
    soup = BeautifulSoup(response.content, 'xml')
    news = soup.find('item')
    data['news'] = {'title': news.title.text, 'description': news.description.text} if news else {}

    return data
