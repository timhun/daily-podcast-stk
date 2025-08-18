import logging
from scripts.utils import load_config, get_symbols

from scripts.data_collector import collect
from scripts.strategy_manager import run as run_strategy
from scripts.market_analyst import analyze
from scripts.script_editor import generate
from scripts.podcast_producer import synthesize
from scripts.upload_manager import upload
from scripts.feed_publisher import publish

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("orchestrator")

def main():
    config = load_config()
    symbols = get_symbols(config)

    for symbol in symbols:
        logger.info(f"=== Pipeline Start: {symbol} ===")

        # 1. 收集資料
        collected = collect()

        # 2. 策略運算
        strat_result = run_strategy(symbol)

        # 3. 市場分析
        analysis = analyze(symbol)

        # 4. 生成腳本
        script_path = generate(symbol, {**strat_result, **analysis})

        # 5. 語音合成
        audio_path = synthesize(script_path)

        # 6. 上傳
        audio_link = upload(audio_path)

        # 7. 發布 RSS
        rss_path = publish(symbol, audio_link)

        logger.info(f"=== Pipeline Done: {symbol}, RSS={rss_path} ===\n")

if __name__ == "__main__":
    main()
