import os
from feedgen.feed import FeedGenerator
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+ 內建

os.makedirs('rss', exist_ok=True)

audio_path = 'podcast/latest/audio.mp3'
script_path = 'podcast/latest/script.txt'

if not os.path.exists(audio_path) or not os.path.exists(script_path):
    print('⚠️ 音檔或逐字稿不存在，無法產生 RSS')
    exit(0)

fg = FeedGenerator()
fg.title('幫幫忙說財經科技投資')
fg.link(href='https://timhun.github.io/daily-podcast-stk/', rel='alternate')
fg.description('每天15分鐘，帶你掌握最新美股、ETF、比特幣、AI 新聞與總經趨勢！')
fg.language('zh-tw')
fg.load_extension('podcast')
fg.podcast.itunes_author('幫幫忙')
fg.podcast.itunes_category('Business', 'Investing')
fg.podcast.itunes_explicit('no')
fg.podcast.itunes_image('https://timhun.github.io/daily-podcast-stk/img/cover.jpg')  # 請自行放 podcast_cover.jpg
fg.podcast.itunes_owner(name='幫幫忙', email='tim.oneway@gmail.com')

with open(script_path) as f:
    summary = f.read()[:200]

# 產生台灣時區的發佈時間
tw_now = datetime.now(ZoneInfo("Asia/Taipei"))
fe = fg.add_entry()
fe.title(f'財經科技投資 Podcast - {tw_now.strftime("%Y-%m-%d")}')
fe.description(summary)
#fe.enclosure('https://timhun.github.io/daily-podcast-stk/podcast/latest/audio.mp3', 0, 'audio/mpeg')
audio_url = 'https://timhun.github.io/daily-podcast-stk/podcast/latest/audio.mp3'
file_size = os.path.getsize(audio_path)  # ← 這是檔案大小，單位是byte
fe.enclosure(audio_url, file_size, 'audio/mpeg')

fe.pubDate(tw_now)
fe.podcast.itunes_author('幫幫忙')
fe.podcast.itunes_explicit('no')
fe.podcast.itunes_duration("15:00")

fg.rss_file('rss/podcast.xml')
print('✅ RSS 產生完畢（台灣時區、含作者/信箱）')