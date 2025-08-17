# scripts/run_pipeline.py
import os
import logging
from datetime import datetime
from .data_collector import collect_from_config
from .strategy_manager import run_pk
from .script_editor import generate_script
from .podcast_producer import synthesize
from .upload_manager import upload_and_prune
from .feed_publisher import publish
from .market_analyst import build_market_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("runner")

def main():
    mode = os.getenv("MODE", "hourly")  # 你的需求：手動執行就跑 hourly
    symbol = os.getenv("SYMBOL", "0050.TW")
    benchmark_map = {"0050.TW": "^TWII", "QQQ": "^NDX"}
    benchmark = benchmark_map.get(symbol)

    logger.info(f"以 {mode} 模式執行，symbol={symbol}")

    if mode in ("collector","auto_collector"):
        collect_from_config()
        return

    if mode in ("strategy","hourly","auto_strategy"):
        # 假設小時線 PK
        run_pk(symbol, benchmark=benchmark, use_hourly=True)

    if mode in ("editor","hourly","auto_editor"):
        strat_json = os.path.join("data", f"strategy_best_{symbol.replace('^','INDEX_')}.json")
        script_path = generate_script("tw" if symbol.endswith(".TW") else "us", symbol, strat_json)
    else:
        script_path = ""

    if mode in ("producer","hourly","auto_producer"):
        if script_path:
            audio_path = synthesize(script_path)  # 產出 wav（stub）
        else:
            audio_path = ""
    else:
        audio_path = ""

    if mode in ("uploader","hourly","auto_uploader"):
        if script_path:
            out_dir = os.path.dirname(script_path)
            link = upload_and_prune(out_dir, hours_gate=True)
        else:
            link = ""
    else:
        link = ""

    if mode in ("publisher","hourly","auto_publisher"):
        if script_path:
            publish("tw" if symbol.endswith(".TW") else "us", script_path, link or "")
    logger.info("pipeline 完成")

if __name__ == "__main__":
    main()