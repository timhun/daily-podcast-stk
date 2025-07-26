import pandas as pd
import requests
import yfinance as yf
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import logging
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 台股假日定義
HOLIDAYS = set(pd.to_datetime([
    "2025-01-01", "2025-02-28", "2025-04-04", "2025-05-01", "2025-06-06",
    "2025-09-17", "2025-10-10"
]).date)

def is_trading_day(date):
    return date.weekday() < 5 and date not in HOLIDAYS

def _twse_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.twse.com.tw",
        "Accept": "application/json"
    })
    return session

def fetch_latest_taiex_from_twse():
    """抓取最新一日大盤收盤價與成交值"""
    today = datetime.today()
    for i in range(5):
        date = today - timedelta(days=i)
        if not is_trading_day(date.date()):
            continue
        date_str = date.strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?type=IND&date={date_str}&response=json"
        try:
            session = _twse_session()
            r = session.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            for row in data.get("data9", []):
                if row[0].strip() == "發行量加權股價指數":
                    close = float(row[2].replace(",", ""))
                    volume = float(row[4].replace(",", "")) * 1e8  # 億元轉新台幣
                    logger.info(f"✅ TWSE 最新加權指數：{close} 點，成交值：{volume:,.0f} 元")
                    return close, volume, date.date()
        except Exception as e:
            logger.warning(f"TWSE 最新資料抓取失敗 ({date_str}): {e}")
    raise RuntimeError("❌ 無法從 TWSE 擷取加權指數最新收盤資料")

def fetch_ma_from_goodinfo():
    """從 Goodinfo 抓取 5MA、10MA、月線與季線點位"""
    url = "https://goodinfo.tw/tw/StockIdxDetail.asp?STOCK_ID=%E5%8A%A0%E6%AC%8A%E6%8C%87%E6%95%B8"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://goodinfo.tw/tw/index.asp"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", class_="b1 p4_2 r10 box_shadow")
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 10 and "5日均價" in cells[0].text:
                ma5 = float(cells[1].text.replace(",", ""))
                ma10 = float(cells[3].text.replace(",", ""))
                ma_month = float(cells[5].text.replace(",", ""))
                ma_quarter = float(cells[7].text.replace(",", ""))
                logger.info(f"✅ Goodinfo 均線：5MA={ma5}, 10MA={ma10}, 月線={ma_month}, 季線={ma_quarter}")
                return {
                    "5MA": ma5,
                    "10MA": ma10,
                    "Monthly": ma_month,
                    "Quarterly": ma_quarter
                }
    except Exception as e:
        logger.error(f"❌ Goodinfo 均線資料抓取失敗: {e}")
    return {}

def get_price_volume_tw(symbol, start_date=None, end_date=None, min_days=60):
    """歷史資料抓取（略）"""
    # 保留原本實作
    raise NotImplementedError("請用原本的 get_price_volume_tw() 實作")

# ✅ 外部統一匯入用
def get_latest_taiex_summary():
    try:
        close, volume, date = fetch_latest_taiex_from_twse()
        ma_data = fetch_ma_from_goodinfo()
        return {
            "date": date.strftime("%Y-%m-%d"),
            "close": close,
            "volume": volume,
            "5MA": ma_data.get("5MA"),
            "10MA": ma_data.get("10MA"),
            "monthly": ma_data.get("Monthly"),
            "quarterly": ma_data.get("Quarterly")
        }
    except Exception as e:
        logger.error(f"❌ 加權指數最新摘要抓取失敗: {e}")
        return {}