from feedgen.feed import FeedGenerator
from datetime import datetime

def generate_rss():
    fg = FeedGenerator()
    fg.title('大叔說財經科技投資')
    fg.author({'name': '大叔', 'email': 'timhun@ms28.hinet.net'})
    fg.link(href='https://timhun.github.io/uncle-finance-podcast/', rel='alternate')
    fg.description('每日財經科技投資資訊')
    fg.language('zh-tw')
    fg.itunes_category({'cat': 'Business', 'sub': 'Investing'})
    fg.itunes_image('https://timhun.github.io/uncle-finance-podcast/img/cover.jpg')
    fg.itunes_explicit('no')

    date = datetime.now().strftime('%Y%m%d')
    fe = fg.add_entry()
    fe.title(f'每日財經播報 - {date}')
    fe.description('每日美股、加密貨幣、AI與經濟新聞分析')
    fe.enclosure(url=f'https://timhun.github.io/uncle-finance-podcast/audio/episode_{date}.mp3', type='audio/mpeg', length='34216300')
    fe.published(datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'))

    fg.rss_file('feed.xml')
