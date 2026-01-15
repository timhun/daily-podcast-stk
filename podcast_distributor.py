import os
import datetime
import pytz
import xml.etree.ElementTree as ET
try:
    from mutagen.mp3 import MP3
except Exception:
    MP3 = None
from feedgen.feed import FeedGenerator
from loguru import logger
import json
from cloud_manager import upload_rss
try:
    from slack_sdk import WebClient
except Exception:
    WebClient = None
import pandas as pd  # 新增：用於計算報酬

# 載入 config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 設置日誌
logger.add(config['logging']['file'], rotation=config['logging']['rotation'])

# 基本常數
B2_BASE = f"https://f005.backblazeb2.com/file/{config['b2_podcast_prefix']}"
RSS_FILE = config['data_paths']['rss']
COVER_URL = "https://timhun.github.io/daily-podcast-stk/img/cover.jpg"

FIXED_DESCRIPTION = """(測試階段)一個適合上班族在最短時間做短線交易策略的節目!
每集節目由涵蓋最新市場數據與 AI 趨勢，專注市值型ETF短線交易策略(因為你沒有無限資金可以東買買西買買，更沒有時間研究個股)！
\n\n讓你在 3 分鐘內快速掌握大盤動向，以獨家研製的短線大盤多空走向，
提供美股每日(SPY,QQQ)的交易策略(喜歡波動小的選SPY/QQQ,波動大的TQQQ/SOXL)。\n\n
提供台股每日(0050或00631L)的交易策略(喜歡波動小的選0050,波動大的00631L)。
\n\n
🔔 訂閱 Apple Podcasts 或 Spotify，掌握每日雙時段更新。掌握每日美股、台股、AI工具與新創投資機會！\n\n
📮 主持人：幫幫忙  \n\n  YT頻道\n 幫幫忙 \n\n https://youtube.com/channel/UC1yYPJ_S8lyEOkeACsX2-SQ?si=DdbwhP6G_vVf_Fv5"""


def summarize_symbol_strategy(symbol, result):
    """抽取單一標的的策略摘要與對戰明細。"""
    if not isinstance(result, dict):
        return None
    best_info = dict(result.get('best') or {})
    best_name = best_info.get('name') or result.get('strategy') or 'N/A'
    best_signals = best_info.get('signals') or result.get('signals', {})
    best_position = best_signals.get('position', 'NEUTRAL')
    best_return = best_info.get('expected_return', result.get('expected_return', 0.0))
    chart_url = best_info.get('chart_url')  # 提取圖表 URL

    strategy_lines = []
    for strat_name, strat in sorted((result.get('strategies') or {}).items()):
        position = strat.get('signals', {}).get('position', 'NEUTRAL')
        expected = strat.get('expected_return', 0.0)
        strategy_lines.append(f"{strat_name} {position} {expected:.2f}%")

    detail = "｜".join(strategy_lines)
    return {
        "symbol": symbol,
        "best_name": best_name,
        "best_position": best_position,
        "best_return": best_return,
        "detail": detail,
        "chart_url": chart_url  # 在返回的字典中包含 URL
    }


def build_strategy_digest(strategy_results, mode=None):
    """生成跨策略的摘要文字，供 RSS 或 UI 顯示。"""
    if not strategy_results:
        return ""
    lines = []
    for symbol in sorted(strategy_results.keys()):
        summary = summarize_symbol_strategy(symbol, strategy_results.get(symbol))
        if not summary:
            continue
        headline = (
            f"{summary['symbol']} 最佳 {summary['best_name']}（{summary['best_position']}，"
            f"{summary['best_return']:.2f}%）"
        )
        if summary["detail"]:
            headline = f"{headline}｜{summary['detail']}"
        if summary["chart_url"]:
            headline = f"{headline}\n圖表: {summary['chart_url']}"  # 附加圖表 URL
        lines.append(headline)
    return "\n".join(lines)


def parse_existing_rss(rss_path):
    existing_entries = []
    if os.path.exists(rss_path):
        try:
            tree = ET.parse(rss_path)
            root = tree.getroot()
            channel = root.find('channel')
            for item in channel.findall('item'):
                entry = {
                    'title': item.find('title').text,
                    'description': item.find('description').text,
                    'enclosure_url': item.find('enclosure').get('url'),
                    'enclosure_length': item.find('enclosure').get('length', '0'),
                    'enclosure_type': item.find('enclosure').get('type', 'audio/mpeg'),
                    'pubDate': item.find('pubDate').text,
                    'guid': item.find('guid').text if item.find('guid') is not None else item.find('enclosure').get('url')
                }
                existing_entries.append(entry)
        except ET.ParseError as e:
            logger.warning(f"RSS 解析錯誤: {e}，重新創建 RSS。")
    return existing_entries

def generate_rss(date, mode, script, audio_url, strategy_results):
    # 初始化 Feed
    fg = FeedGenerator()
    fg.load_extension("podcast")
    fg.id("https://timhun.github.io/daily-podcast-stk")
    fg.title("幫幫忙說AI投資")
    fg.author({"name": "幫幫忙AI投資腦", "email": "bbm2330pub@gmail.com"})
    fg.link(href="https://timhun.github.io/daily-podcast-stk", rel="alternate")
    fg.language("zh-TW")
    fg.description("掌握美股台股、科技、AI 與投資機會，每日兩集！")
    fg.logo(COVER_URL)
    fg.link(href=f"{B2_BASE}/podcast.xml", rel="self")
    fg.podcast.itunes_category("Business", "Investing")
    fg.podcast.itunes_image(COVER_URL)
    fg.podcast.itunes_explicit("no")
    fg.podcast.itunes_author("幫幫忙AI投資腦")
    fg.podcast.itunes_owner(name="幫幫忙AI投資腦", email="tim.oneway@gmail.com")

    # 加入歷史集數
    existing_entries = parse_existing_rss(RSS_FILE)
    for entry in existing_entries:
        fe = fg.add_entry()
        fe.title(entry['title'])
        fe.description(entry['description'])
        fe.enclosure(entry['enclosure_url'], entry['enclosure_length'], entry['enclosure_type'])
        fe.pubDate(entry['pubDate'])
        fe.guid(entry['guid'], permalink=True)

    # 查找最新集數資料夾
    episodes_dir = config['data_paths']['podcast']
    folder = f"{date}_{mode}"
    base_path = os.path.join(episodes_dir, folder)
    audio_filename = f"daily-podcast-stk-{date}_{mode}.mp3"
    audio = os.path.join(base_path, audio_filename)

    if not os.path.exists(audio):
        logger.error(f"⚠️ 找不到音頻檔案：{audio}")
        raise FileNotFoundError(f"⚠️ 找不到音頻檔案：{audio}")

    # 提取音頻時長
    try:
        if MP3 is None:
            raise RuntimeError("mutagen not available")
        mp3 = MP3(audio)
        duration = int(mp3.info.length)
    except Exception as e:
        logger.warning(f"⚠️ 讀取 mp3 時長失敗：{e}")
        duration = None

    # 設置發布日期
    tz = pytz.timezone("Asia/Taipei")
    pub_date = tz.localize(datetime.datetime.strptime(date, "%Y%m%d"))
    title = f"幫幫忙每日投資快報 - {'台股' if mode == 'tw' else '美股'}（{date}_{mode}）"

    # 使用腳本作為描述並附加策略摘要
    #full_description = FIXED_DESCRIPTION + script[:200] + "..." if script else FIXED_DESCRIPTION
    full_description = FIXED_DESCRIPTION 
    #digest = build_strategy_digest(strategy_results, mode)
    #if digest:
    #    full_description = f"{full_description}\n\n策略戰報\n{digest}"

    # 新增集數
    fe = fg.add_entry()
    fe.id(audio_url)
    fe.title(title)
    fe.description(full_description)
    fe.content(full_description, type="CDATA")
    fe.enclosure(audio_url, str(os.path.getsize(audio)), "audio/mpeg")
    fe.pubDate(pub_date)
    if duration:
        fe.podcast.itunes_duration(str(datetime.timedelta(seconds=duration)))
    fe.podcast.itunes_summary(full_description[:500])
    #fe.podcast.itunes_keywords("投資, AI, 美股, 台股, ETF")

    # 輸出 RSS
    try:
        os.makedirs(os.path.dirname(RSS_FILE), exist_ok=True)
        fg.rss_file(RSS_FILE)
        logger.info(f"✅ 已產生 RSS Feed：{RSS_FILE}")
        rss_url = upload_rss(RSS_FILE)
        logger.info(f"RSS 上傳至 B2: {rss_url}")
        if WebClient is not None:
            notify_slack_enhanced(strategy_results, mode)
        else:
            logger.warning("Slack SDK not available; skipping Slack notification.")
    except Exception as e:
        logger.error(f"⚠️ 產生 RSS 檔案失敗: {e}")
        raise IOError(f"⚠️ 產生 RSS 檔案失敗: {e}")

def notify_slack_simple(date, mode, audio_url):  # 原notify_slack，重命名
    try:
        if WebClient is None:
            raise RuntimeError("Slack SDK not available")
        client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))
        message = f"New {mode.upper()} podcast episode for {date} is ready! Audio: {audio_url}"
        client.chat_postMessage(channel=os.getenv('SLACK_CHANNEL'), text=message)
        logger.info(f"已發送 Slack 通知，{mode} 版 {date} 集數")
        print(f"已發送 Slack 通知，{mode} 版 {date} 集數")
    
    except Exception as e:
        logger.error(f"Slack 通知失敗：{str(e)}")
        raise

def notify_slack_enhanced(strategy_results, mode):
    """增強Slack通知：動態生成指定格式"""
    try:
        if WebClient is None:
            raise RuntimeError("Slack SDK not available")
        client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))
        
        # 日期格式
        TW_TZ = pytz.timezone("Asia/Taipei")
        today = datetime.datetime.now(TW_TZ)
        weekday_ch = ['一', '二', '三', '四', '五', '六', '日'][today.weekday()]
        date_str = f"{today.year}/{today.month:02d}/{today.day:02d}（{weekday_ch}）"
        
        # 提取QQQ和0050結果
        qqq_symbol = 'QQQ' if mode == 'us' else None
        tw_symbol = '0050.TW' if mode == 'tw' else None
        
        # QQQ部分 (us模式)
        qqq_summary = summarize_symbol_strategy(qqq_symbol, strategy_results.get(qqq_symbol)) if qqq_symbol else None
        qqq_position = strategy_results.get(qqq_symbol, {}).get('signals', {}).get('position', 'NEUTRAL') if qqq_symbol else 'NEUTRAL'
        qqq_action = {'LONG': '買入', 'NEUTRAL': '持有', 'SHORT': '賣出'}.get(qqq_position, '持有')
        qqq_yesterday_return = calculate_yesterday_return('QQQ')  # 函數計算
        qqq_position_suggest = "加倉至 90%" if strategy_results.get(qqq_symbol, {}).get('expected_return', 0) > 0.1 else "持倉 70%"
        qqq_best_line = (
            f"最佳策略：{qqq_summary['best_name']}（{qqq_summary['best_position']}，{qqq_summary['best_return']:.2f}%）"
            if qqq_summary else "最佳策略：暫無資料"
        )
        qqq_detail_line = (
            f"策略對戰：{qqq_summary['detail']}" if qqq_summary and qqq_summary["detail"] else "策略對戰：暫無資料"
        )
        qqq_chart_line = f"策略圖表：{qqq_summary['chart_url']}" if qqq_summary and qqq_summary.get('chart_url') else ""
        
        # 0050部分 (tw模式)
        tw_summary = summarize_symbol_strategy(tw_symbol, strategy_results.get(tw_symbol)) if tw_symbol else None
        tw_position = strategy_results.get(tw_symbol, {}).get('signals', {}).get('position', 'NEUTRAL') if tw_symbol else 'NEUTRAL'
        tw_action = {'LONG': '買入', 'NEUTRAL': '持有', 'SHORT': '賣出'}.get(tw_position, '持有')
        tw_yesterday_return = calculate_yesterday_return('0050.TW')
        tw_position_suggest = "持倉 70%" if strategy_results.get(tw_symbol, {}).get('expected_return', 0) < 0.1 else "加倉至 90%"
        tw_best_line = (
            f"最佳策略：{tw_summary['best_name']}（{tw_summary['best_position']}，{tw_summary['best_return']:.2f}%）"
            if tw_summary else "最佳策略：暫無資料"
        )
        tw_detail_line = (
            f"策略對戰：{tw_summary['detail']}" if tw_summary and tw_summary["detail"] else "策略對戰：暫無資料"
        )
        tw_chart_line = f"策略圖表：{tw_summary['chart_url']}" if tw_summary and tw_summary.get('chart_url') else ""
        
        message = f"""🗓 日期：{date_str}

🔹【QQQ 策略】
{qqq_best_line}
{qqq_detail_line}
{qqq_chart_line}
當前操作：模擬{qqq_action}
昨日報酬：{qqq_yesterday_return:+.2f}%

🔹【0050 策略】
{tw_best_line}
{tw_detail_line}
{tw_chart_line}
當前操作：模擬{tw_action}
昨日報酬：{tw_yesterday_return:+.2f}%

📈 模擬倉位變動建議（僅供參考）：
QQQ：{qqq_position_suggest}
0050：{tw_position_suggest}"""
        
        client.chat_postMessage(channel=os.getenv('SLACK_CHANNEL'), text=message)
        logger.info(f"已發送增強 Slack 通知，{mode} 版 {date_str}")
        print(f"已發送增強 Slack 通知，{mode} 版 {date_str}")
    
    except Exception as e:
        logger.error(f"增強 Slack 通知失敗：{str(e)}")
        raise

def calculate_yesterday_return(symbol):
    """計算昨日報酬：從CSV最後兩日close計算"""
    try:
        file_path = f"{config['data_paths']['market']}/daily_{symbol.replace('^', '').replace('.', '_').replace('-', '_')}.csv"
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            if len(df) >= 2:
                return ((df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]) * 100
        return 0.0
    except Exception as e:
        logger.error(f"計算 {symbol} 昨日報酬失敗: {e}")
        return 0.0

if __name__ == "__main__":
    date = datetime.datetime.now(pytz.timezone("Asia/Taipei")).strftime("%Y%m%d")
    mode = os.getenv("PODCAST_MODE", "tw").lower()
    script_path = f"{config['data_paths']['podcast']}/{date}_{mode}/daily-podcast-stk-{date}_{mode}.txt"
    audio_url = f"{B2_BASE}/daily-podcast-stk-{date}_{mode}.mp3"
    with open(script_path, 'r', encoding='utf-8') as f:
        script = f.read().strip()
    generate_rss(date, mode, script, audio_url)
