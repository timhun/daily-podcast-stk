import os, json, logging, argparse, pytz
from datetime import datetime
from feedgen.feed import FeedGenerator
import requests

os.makedirs("logs", exist_ok=True)
logging.basicConfig(filename="logs/feed_publisher.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("feed")

def tpe_date():
    return datetime.now(pytz.timezone("Asia/Taipei")).strftime("%Y%m%d")

def build_feed(mode, site_base):
    fg = FeedGenerator()
    fg.title("幫幫忙說財經科技投資" + ("（美股）" if mode=="us" else "（台股）"))
    fg.link(href=f"{site_base}/docs/rss/podcast_{mode}.xml", rel='self')
    fg.description("每日兩檔：06:00美股、14:00台股。台灣口吻、重點清楚。")
    fg.language("zh-tw")
    return fg

def add_episode(fg, mode, site_base, date_str):
    folder = f"{site_base}/docs/podcast/{date_str}_{mode}"
    mp3_url = f"{site_base}/podcast/{date_str}_{mode}/audio.mp3"  # 以 Pages 路徑為準
    fe = fg.add_entry()
    fe.title(f"{'美股' if mode=='us' else '台股'}播報 {date_str}")
    fe.link(href=mp3_url)
    fe.description("自動化每日播客：幫幫忙說財經科技投資")
    fe.enclosure(mp3_url, 0, 'audio/mpeg')
    fe.pubDate(datetime.now(pytz.timezone("Asia/Taipei")))
    return fg

def notify_slack(channel, text):
    token = os.environ.get("SLACK_BOT_TOKEN","")
    if not token: 
        return
    resp = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}","Content-Type":"application/json"},
        json={"channel": os.environ.get("SLACK_CHANNEL", channel), "text": text})
    try:
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Slack fail: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["us","tw"], required=True)
    args = parser.parse_args()

    cfg = json.load(open("config.json","r",encoding="utf-8"))
    site_base = cfg["site_base"]
    date_str = tpe_date()

    fg = build_feed(args.mode, site_base)
    fg = add_episode(fg, args.mode, site_base, date_str)

    os.makedirs("docs/rss", exist_ok=True)
    out = f"docs/rss/podcast_{args.mode}.xml"
    fg.rss_file(out, pretty=True)
    logger.info(f"RSS saved -> {out}")

    # 同時更新總 RSS（簡化版：只指向兩個子 feed）
    with open("docs/rss/podcast.xml","w",encoding="utf-8") as g:
        g.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<feeds>
  <feed url="{site_base}/docs/rss/podcast_us.xml" />
  <feed url="{site_base}/docs/rss/podcast_tw.xml" />
</feeds>""")

    audio_url_file = f"docs/podcast/{date_str}_{args.mode}/archive_audio_url.txt"
    audio_url = open(audio_url_file,"r",encoding="utf-8").read().strip() if os.path.exists(audio_url_file) else "(no url)"
    notify_slack("#podcast", f"[{date_str}] {args.mode.upper()} 已上架：{audio_url}")

if __name__=="__main__":
    main()
