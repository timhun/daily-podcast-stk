# scripts/institutional_investors_scraper.py
import requests
import json
import os
import logging
from datetime import datetime, timedelta
import pytz

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_institutional_investors(output_file="data/institutional_investors.json"):
    try:
        # 設置台北時區
        taipei_tz = pytz.timezone('Asia/Taipei')
        target_date = (datetime.now(taipei_tz) - timedelta(days=1)).strftime('%Y-%m-%d')

        # 從 TWSE API 獲取三大法人數據
        url = "https://openapi.twse.com.tw/v1/institutional/investors"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # 假設取最新一天數據
        latest_data = data[-1] if data else {}
        institutional_data = {
            "date": target_date,
            "institutional_investors": {
                "foreign_investors": float(latest_data.get("ForeignInvestorsNetBuySell", 0)) / 1e8,
                "investment_trust": float(latest_data.get("InvestmentTrustNetBuySell", 0)) / 1e8,
                "dealers": float(latest_data.get("DealersNetBuySell", 0)) / 1e8
            },
            "data_source": "TWSE"
        }
        logger.info("成功獲取三大法人數據")

        # 儲存 JSON
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(institutional_data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ 已儲存 {output_file}")

        return institutional_data
    except Exception as e:
        logger.error(f"獲取三大法人數據失敗: {e}")
        raise

if __name__ == "__main__":
    fetch_institutional_investors()
