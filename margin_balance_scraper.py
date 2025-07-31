import requests
import json
import os
import logging
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TWSE_STOCK_IDS = {
    "0050": "0050",
    "00631L": "00631L",
    "2330": "2330"
}

def get_today_date_str():
    tz = pytz.timezone("Asia/Taipei")
    return datetime.now(tz).strftime("%Y-%m-%d")

def fetch_from_twse(stock_id):
    try:
        url = f"https://openapi.twse.com.tw/v1/margin_short/{stock_id}"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()

        if not data:
            logger.warning(f"TWSE 無資料：{stock_id}")
            return None

        latest = data[-1]
        return {
            "date": datetime.strptime(latest["Date"], "%Y%m%d").strftime("%Y-%m-%d"),
            "stock_id": stock_id,
            "margin_balance": int(latest.get("MarginBalance") or 0),
            "short_balance": int(latest.get("ShortBalance") or 0),
            "source": "TWSE"
        }
    except Exception as e:
        logger.warning(f"TWSE 擷取失敗（{stock_id}）: {e}")
        return None

def fetch_from_cnyes(stock_id):
    try:
        url = f"https://www.cnyes.com/twstock/{stock_id}/margin-trading"
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 9:
                try:
                    date_str = cols[0].text.strip()
                    margin = int(cols[4].text.strip().replace(",", "").replace("--", "0"))
                    short = int(cols[8].text.strip().replace(",", "").replace("--", "0"))
                    return {
                        "date": date_str,
                        "stock_id": stock_id,
                        "margin_balance": margin,
                        "short_balance": short,
                        "source": "Cnyes"
                    }
                except Exception:
                    continue
        logger.warning(f"Cnyes 無法解析資料：{stock_id}")
        return None
    except Exception as e:
        logger.warning(f"Cnyes 擷取失敗（{stock_id}）: {e}")
        return None

def fetch_margin_data(stock_ids):
    all_data = {}
    today_str = get_today_date_str()

    for stock_id in stock_ids:
        data = fetch_from_twse(stock_id)
        if not data or data["date"] != today_str:
            logger.warning(f"⚠️ TWSE 資料缺失或非今日，嘗試 Cnyes：{stock_id}")
            data = fetch_from_cnyes(stock_id)
        if data:
            all_data[stock_id] = data
        else:
            logger.error(f"❌ 無法取得資料：{stock_id}")
    return all_data

def save_to_json(data, path="data/margin_balance.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ 已儲存至 {path}")

if __name__ == "__main__":
    logger.info("🚀 開始抓取融資券餘額資料")
    stock_list = list(TWSE_STOCK_IDS.values())
    result = fetch_margin_data(stock_list)
    save_to_json(result)