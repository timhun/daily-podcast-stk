from feedgen.feed import FeedGenerator
import os, datetime, json

def build():
    with open("config.json") as f:
        config = json.load(f)

    fg = FeedGenerator()
    fg.title(config["podcast_title"])
    fg.link(href=config["base_url"], rel='alternate')
    fg.description("每日自動播報財經科技投資資訊")

    for mp3 in sorted(os.listdir("episodes")):
        date_str = mp3.replace(".mp3", "")
        url = f"{config['base_url']}/episodes/{mp3}"
        pub_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")

        fe = fg.add_entry()
        fe.title(f"{date_str} 幫幫忙播報")
        fe.pubDate(pub_date)
        fe.enclosure(url, 0, "audio/mpeg")

    fg.rss_file("feed/rss.xml")

if __name__ == "__main__":
    build()
