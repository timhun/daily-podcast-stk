import os
from feedgen.feed import FeedGenerator
from datetime import datetime

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

with open(script_path) as f:
    summary = f.read()[:200]

d = datetime.now().strftime('%Y-%m-%d')
fe = fg.add_entry()
fe.title(f'財經科技投資 Podcast - {d}')
fe.description(summary)
fe.enclosure(f'https://timhun.github.io/daily-podcast-stk/podcast/latest/audio.mp3', 0, 'audio/mpeg')
fe.pubDate(datetime.now())

fg.rss_file('rss/podcast.xml')
print('✅ RSS 產生完畢')