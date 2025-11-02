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

def get_market_data_path(symbol: str, timeframe: str = 'daily') -> str:
    """
    Generates the standardized path for market data CSV files.
    Example: get_market_data_path('0050.TW', 'daily') -> 'data/market/daily_0050_TW.csv'
    """
    sanitized_symbol = symbol.replace('^', '').replace('.', '_')
    return f"{DATA_DIR}/market/{timeframe}_{sanitized_symbol}.csv"