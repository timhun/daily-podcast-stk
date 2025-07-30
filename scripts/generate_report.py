# scripts/generate_report.py
import json
import os
import logging
from datetime import datetime, timedelta
import pytz

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_report(taiex_file="data/taiex_data.json", inst_file="data/institutional_investors.json", output_file="data/market_data_tw.json"):
    try:
        # 設置台北時區
        taipei_tz = pytz.timezone('Asia/Taipei')
        target_date = (datetime.now(taipei_tz) - timedelta(days=1)).strftime('%Y-%m-%d')

        # 讀取 TAIEX 數據
        if not os.path.exists(taiex_file):
            logger.error(f"TAIEX 數據檔案 {taiex_file} 不存在")
            raise FileNotFoundError(f"TAIEX 數據檔案 {taiex_file} 不存在")
        with open(taiex_file, "r", encoding="utf-8") as f:
            taiex_data = json.load(f)

        # 讀取三大法人數據
        if not os.path.exists(inst_file):
            logger.error(f"三大法人數據檔案 {inst_file} 不存在")
            raise FileNotFoundError(f"三大法人數據檔案 {inst_file} 不存在")
        with open(inst_file, "r", encoding="utf-8") as f:
            inst_data = json.load(f)

        # 合併數據
        market_data = {
            "date": target_date,
            "taiex": taiex_data["taiex"],
            "trading_volume": taiex_data["trading_volume"],
            "institutional_investors": inst_data["institutional_investors"],
            "moving_averages": taiex_data["moving_averages"],
            "macd": taiex_data["macd"],
            "data_source": f"{taiex_data['data_source']}/TWSE"
        }

        # 儲存最終報告
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(market_data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ 已生成報告 {output_file}")

        return market_data
    except Exception as e:
        logger.error(f"生成報告失敗: {e}")
        raise

if __name__ == "__main__":
    generate_report()
