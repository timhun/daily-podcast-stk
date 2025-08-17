import os
import sys
import json
import logging
import datetime
import pandas as pd

from strategy_manager import load_market_data, save_strategy, normalize_symbol

# ===== Logging =====
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ===== Config =====
CONFIG_PATH = "config.json"

def load_config():
    if not os.path.exists(CONFIG_PATH):
        logger.error(f"⚠️ 找不到 {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_podcast_script(symbol: str, mode: str = "hourly"):
    """
    根據行情生成逐字稿 (示範: 只寫 summary，不做完整 NLP)
    """
    df = load_market_data(symbol, use_hourly=(mode == "hourly"))
    if df is None or df.empty:
        logger.error(f"{symbol} 無法生成逐字稿，缺少數據")
        return None

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else None

    close = latest.get("Close", None)
    pct = "N/A"
    if prev is not None and "Close" in prev and pd.notna(prev["Close"]):
        try:
            pct = ((float(close) - float(prev["Close"])) / float(prev["Close"]) * 100)
            pct = round(pct, 2)
        except Exception as e:
            logger.error(f"計算漲跌幅失敗: {e}")

    script = f"{symbol} 最新收盤 {close}, 漲跌 {pct}%"
    logger.info(f"已生成逐字稿: {script}")
    return script

def main():
    config = load_config()
    symbols = config.get("symbols", [])
    podcast_mode = os.environ.get("PODCAST_MODE", "tw")

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"🚀 Pipeline 開始: {now}, 模式={podcast_mode}")

    mode = os.environ.get("MODE", "hourly")

    for sym in symbols:
        script = generate_podcast_script(sym, mode=mode)
        if script:
            norm_sym = normalize_symbol(sym)
            out_dir = f"docs/podcast/{datetime.date.today().strftime('%Y%m%d')}_{podcast_mode}"
            os.makedirs(out_dir, exist_ok=True)
            out_path = f"{out_dir}/script_{norm_sym}.txt"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(script)
            logger.info(f"已寫入逐字稿 {out_path}")

    logger.info("✅ Pipeline 完成")

if __name__ == "__main__":
    main()