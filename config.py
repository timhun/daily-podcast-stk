# config.py
US_TICKERS = ['^IXIC', '^GSPC', 'QQQ', 'SPY', 'BTC-USD', 'GC=F']
TW_TICKERS = ['^TWII', '0050.TW', '2330.TW']

US_MARKET_NAMES = {
    '^IXIC': '納斯達克指數',
    '^GSPC': '標普500指數',
    'QQQ': 'Invesco QQQ Trust',
    'SPY': 'SPDR S&P 500 ETF',
    'BTC-USD': '比特幣',
    'GC=F': '黃金期貨'
}

TW_MARKET_NAMES = {
    '^TWII': '台股加權指數',
    '0050.TW': '元大台灣50 ETF',
    '2330.TW': '台積電'
}

DATA_DIR = 'data'
DOCS_DIR = 'docs/podcast'