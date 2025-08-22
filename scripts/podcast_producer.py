#podcast_producer.py
import os, json, logging, argparse, asyncio
import edge_tts
from datetime import datetime
import pytz

os.makedirs("logs", exist_ok=True)
logging.basicConfig(filename="logs/podcast_producer.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("tts")

def load_cfg():
    return json.load(open("config.json","r",encoding="utf-8"))

def today_tpe():
    return datetime.now(pytz.timezone("Asia/Taipei")).strftime("%Y%m%d")

async def tts(text, voice, rate, volume, out):
    com = edge_tts.Communicate(text, voice=voice, rate=rate, volume=volume)
    await com.save(out)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["us","tw"], required=True)
    args = parser.parse_args()

    cfg = load_cfg()
    date_str = today_tpe()
    folder = f"docs/podcast/{date_str}_{args.mode}"
    script_path = f"{folder}/script.txt"
    audio_path = f"{folder}/audio.mp3"
    assert os.path.exists(script_path), "script.txt not found"

    text = open(script_path,"r",encoding="utf-8").read()
    voice = cfg["tts"]["voice"]
    rate  = cfg["tts"]["rate"]
    volume= cfg["tts"]["volume"]

    asyncio.run(tts(text, voice, rate, volume, audio_path))
    logger.info(f"TTS saved -> {audio_path}")

if __name__=="__main__":
    main()
