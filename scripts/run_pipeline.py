# scripts/run_pipeline.py
import os
import json
import logging
from datetime import datetime

from data_collector import collect_from_config
from strategy_manager import run_pk
from script_editor import generate_script
from podcast_producer import synthesize
from upload_manager import upload_and_prune
from feed_publisher import publish
from market_analyst import build_market_summary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("runner")


def load_config_symbols():
    """讀取 config.json 內的 symbols"""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
            return cfg.get("symbols", [])
    except Exception as e:
        logger.error(f"讀取 config.json 失敗: {e}")
        return []


def normalize_symbol_for_file(symbol: str) -> str:
    """
    將 ^TWII → INDEX_TWII 這種名稱轉換，避免存檔出問題
    """
    if symbol.startswith("^"):
        return "INDEX_" + symbol[1:]
    return symbol.replace("^", "INDEX_")


def main():
    # 預設：手動執行時跑 hourly
    mode = os.getenv("MODE", "hourly")
    symbol = os.getenv("SYMBOL", "")

    if not symbol:
        # 若沒有指定 symbol，就從 config.json 取第一個
        symbols = load_config_symbols()
        if not symbols:
            logger.error("config.json 沒有找到任何 symbol")
            return
        symbol = symbols[0]

    benchmark_map = {"0050.TW": "^TWII", "QQQ": "^NDX"}
    benchmark = benchmark_map.get(symbol)

    logger.info(f"以 {mode} 模式執行，symbol={symbol}, benchmark={benchmark}")

    # === Collector ===
    if mode in ("collector", "auto_collector"):
        collect_from_config()
        return

    # === Strategy (小時線 PK) ===
    if mode in ("strategy", "hourly", "auto_strategy"):
        run_pk(symbol, benchmark=benchmark, use_hourly=True)

    # === Editor (生成逐字稿) ===
    strat_json = ""
    script_path = ""
    if mode in ("editor", "hourly", "auto_editor"):
        strat_json = os.path.join("data", f"strategy_best_{normalize_symbol_for_file(symbol)}.json")
        script_path = generate_script(
            "tw" if symbol.endswith(".TW") else "us",
            symbol,
            strat_json
        )
        logger.info(f"逐字稿生成完成: {script_path}")

    # === Producer (合成音訊) ===
    audio_path = ""
    if mode in ("producer", "hourly", "auto_producer"):
        if script_path:
            audio_path = synthesize(script_path)
            logger.info(f"音訊合成完成: {audio_path}")

    # === Uploader (上傳) ===
    link = ""
    if mode in ("uploader", "hourly", "auto_uploader"):
        if script_path:
            out_dir = os.path.dirname(script_path)
            link = upload_and_prune(out_dir, hours_gate=True)
            logger.info(f"已上傳並清理, link={link}")

    # === Publisher (RSS feed) ===
    if mode in ("publisher", "hourly", "auto_publisher"):
        if script_path:
            publish("tw" if symbol.endswith(".TW") else "us", script_path, link or "")

    logger.info("✅ pipeline 完成")


if __name__ == "__main__":
    main()