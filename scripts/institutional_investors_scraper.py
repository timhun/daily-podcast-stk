# scripts/institutional_investors_scraper.py
import requests
import json
import os
import logging
from datetime import datetime
import pytz
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def safe_float(value):
    """安全將值轉成 float，失敗回傳 0.0"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def fetch_institutional_investors(output_file="data/institutional_investors.json"):
    """
    從 TWSE API 取得三大法人買賣超資料並存成 JSON 檔

    Returns:
        dict or None: 取得的法人資料，失敗回傳 None。
    """
    try:
        # 設置台北時區
        taipei_tz = pytz.timezone('Asia/Taipei')
        target_date = datetime.now(taipei_tz).strftime('%Y-%m-%d')

        # 設置 requests 重試機制
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)

        url = "https://openapi.twse.com.tw/v1/institutional/investors"
        response = session.get(url, timeout=10)
        response.raise_for_status()

        if not response.text or response.text.isspace():
            logger.warning(f"TWSE API 回傳空數據，可能是休市日（{target_date}）")
            return None

        try:
            data = response.json()
        except ValueError as e:
            logger.error(f"無法解析 TWSE API 回應為 JSON: {response.text}")
            raise ValueError(f"❌ 無法解析 TWSE API 回應: {e}")

        if not 
            logger.warning(f"TWSE API 回傳空數據，可能是休市日（{target_date}）")
            return None

        latest_data = data[-1] if data else {}
        api_date = latest_data.get("Date")

        try:
            api_date_obj = datetime.strptime(api_date, '%Y%m%d')
        except Exception:
            logger.warning(f"API 日期格式不正確: {api_date}")
            return None

        if api_date_obj.date() != datetime.now(taipei_tz).date():
            logger.warning(f"最新數據日期 ({api_date_obj.strftime('%Y-%m-%d')}) 與目標日期 ({target_date}) 不符")
            return None

        institutional_data = {
            "date": target_date,
            "institutional_investors": {
                "foreign_investors": safe_float(latest_data.get("ForeignInvestorsNetBuySell")) / 1e8,
                "investment_trust": safe_float(latest_data.get("InvestmentTrustNetBuySell")) / 1e8,
                "dealers": safe_float(latest_data.get("DealersNetBuySell")) / 1e8
            },
            "data_source": "TWSE"
        }

        logger.info("成功獲取三大法人數據")

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(institutional_data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ 已儲存 {output_file}")

        return institutional_data

    except requests.exceptions.RequestException as e:
        logger.error(f"獲取 TWSE API 數據失敗: {e}")
        return None
    except Exception as e:
        logger.error(f"處理三大法人數據失敗: {e}")
        raise

if __name__ == "__main__":
    fetch_institutional_investors()
