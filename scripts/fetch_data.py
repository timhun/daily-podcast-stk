import yfinance as yf
import requests
import json
from datetime import datetime, timedelta
from logger import setup_logger, log_error_and_notify

logger = setup_logger()

def fetch_indices():
    indices = ['^DJI', '^IXIC', '^GSPC', '^SOX', 'QQQ', 'SPY']
    data = {}
    for idx in indices:
        try:
            ticker = yf.Ticker(idx)
            hist = ticker.history(period='2d')
            if len(hist) < 2:
                log_error_and_notify(f"Failed to fetch data for {idx}")
            close = hist['Close'][-1]
            prev_close = hist['Close'][-2]
            change = ((close - prev_close) / prev_close) * 100
            data[idx] = {'close': round(close, 2), 'change': round(change, 2)}
            logger.info(f"Fetched {idx}: close={close}, change={change}%")
        except Exception as e:
            log_error_and_notify(f"Error fetching {idx}: {str(e)}")
    return data

def fetch_crypto(api_key):
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {'X-CMC_PRO_API_KEY': api_key}
    params = {'symbol': 'BTC'}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()['data']['BTC']['quote']['USD']
        logger.info(f"Fetched BTC: price={data['price']}, change={data['percent_change_24h']}%")
        return {'price': round(data['price'], 2), 'change': round(data['percent_change_24h'], 2)}
    except Exception as e:
        log_error_and_notify(f"Error fetching BTC: {str(e)}")

def fetch_gold():
    try:
        data = {'price': 3354.76, 'change': 0.92}  # 假設數據，實際需替換
        logger.info(f"Fetched Gold: price={data['price']}, change={data['change']}%")
        return data
    except Exception as e:
        log_error_and_notify(f"Error fetching Gold: {str(e)}")

def fetch_top_stocks():
    try:
        stocks = ['WLGS', 'ABVE', 'BTOG', 'NCNA', 'OPEN']
        logger.info(f"Fetched top stocks: {stocks}")
        return stocks
    except Exception as e:
        log_error_and_notify(f"Error fetching top stocks: {str(e)}")

def fetch_quote():
    try:
        with open('data/quotes.json', 'r', encoding='utf-8') as f:
            quotes = json.load(f)
        import random
        quote = random.choice(quotes)
        logger.info(f"Fetched quote: {quote['text']}")
        return quote
    except Exception as e:
        log_error_and_notify(f"Error fetching quote: {str(e)}")
