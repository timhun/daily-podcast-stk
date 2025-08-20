import os
import datetime
import pytz
from mutagen.mp3 import MP3
from feedgen.feed import FeedGenerator
import logging
import argparse

# ===== 日誌 =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ===== 常數 =====
SITE_URL = "https://timhun.github.io/daily-podcast-stk"
# 若你想保留 B2 推導連結，設定環境變數 B2_BASE（ex: https://f005.backblazeb2.com/file/daily-podcast-stk）
B2_BASE = os.getenv("B2_BASE", "").rstrip("/")
COVER_URL = f"{SITE_URL}/img/cover.jpg"

FIXED_DESCRIPTION = (
    "(測試階段)一個適合上班族在最短時間做短線交易策略的節目!\n"
    "每集節目由涵蓋最新市場數據與 AI 趨勢，專注市值型ETF短線交易策略(因為你沒有無限資金可以東買買西買買，更沒有時間研究個股)！\n\n"
    "讓你在 7 分鐘內快速掌握大盤動向，以獨家研製的短線大盤多空走向，\n"
    "提供美股每日(SPY,QQQ)的交易策略(喜歡波動小的選SPY/QQQ,波動大的TQQQ/SOXL)。\n\n"
    "提供台股每日(0050或00631L)的交易策略(喜歡波動小的選0050,波動大的00631L)。\n\n"
    "🔔 訂閱 Apple Podcasts 或 Spotify，掌握每日雙時段更新。掌握每日美股、台股、AI工具與新創投資機會！\n\n"
    "📮 主持人：幫幫忙"
)

def pick_folder_by_mode(mode: str) -> str:
    """
    依 Asia/Taipei 時區優先找「今天」的 YYYYMMDD_mode，
    若無，再回退「昨天」；再無，改用 docs/podcast 內最新的 *_mode。
    """
    tz = pytz.timezone("Asia/Taipei")
    now_tpe = datetime.datetime.now(tz)
    today_str = now_tpe.strftime("%Y%m%d")
    yday_str = (now_tpe - datetime.timedelta(days=1)).strftime("%Y%m%d")

    episodes_dir = "docs/podcast"
    candidates = [f"{today_str}_{mode}", f"{yday_str}_{mode}"]

    for folder in candidates:
        p = os.path.join(episodes_dir, folder)
        if os.path.isdir(p):
            logger.info(f"✅ 選到資料夾（優先清單）：{folder}")
            return folder

    # 最後退路：找所有符合 *_mode 的資料夾，取最新
    matching = sorted(
        [f for f in os.listdir(episodes_dir)
         if os.path.isdir(os.path.join(episodes_dir, f)) and f.endswith(f"_{mode}")],
        reverse=True
    )
    if matching:
        logger.warning(f"⚠️ 找不到 {today_str}_{mode}/{yday_str}_{mode}，改用最新：{matching[0]}")
        return matching[0]

    raise FileNotFoundError(f"⚠️ 找不到任何符合模式 '{mode}' 的 podcast 資料夾")

def build_audio_url(base_path: str, folder: str) -> str:
    """
    先讀 archive_audio_url.txt；
    若無，fallback 到 GitHub Pages 音檔網址（強烈建議，因為 mp3 已 commit 到 docs/）。
    若你仍想推導 B2 連結（可能尚未上傳），最後才嘗試使用 B2_BASE 推導。
    """
    archive_url_file = os.path.join(base_path, "archive_audio_url.txt")
    if os.path.exists(archive_url_file):
        with open(archive_url_file, "r", encoding="utf-8") as f:
            url = f.read().strip()
        if url:
            logger.info(f"🧾 使用 B2 連結（來自 archive_audio_url.txt）：{url}")
            return url
        logger.warning("⚠️ archive_audio_url.txt 為空，將使用 fallback")

    # Fallback 1: GitHub Pages 靜態檔（推薦，因 mp3 已在 docs/ 內）
    gh_pages_url = f"{SITE_URL}/podcast/{folder}/audio.mp3"
    logger.warning(f"⚠️ 使用 GitHub Pages fallback 音檔連結：{gh_pages_url}")
    return gh_pages_url

    # 若你想把 B2 推導放在 GH fallback 前面，改為：
    # if B2_BASE:
    #     b2_url = f"{B2_BASE}/daily-podcast-stk-{folder}.mp3"
    #     logger.warning(f"⚠️ 使用 B2 推導連結（可能尚未上傳完成）：{b2_url}")
    #     return b2_url

def generate_rss(mode: str):
    # ===== 初始化 Feed =====
    fg = FeedGenerator()
    fg.load_extension("podcast")
    fg.id(SITE_URL)
    fg.title("幫幫忙說AI.投資")
    fg.author({"name": "幫幫忙AI投資腦", "email": "tim.oneway@gmail.com"})
    fg.link(href=SITE_URL, rel="alternate")
    fg.language("zh-TW")
    fg.description("掌握美股台股、科技、AI 與投資機會，每日兩集！")
    fg.logo(COVER_URL)
    fg.link(href=f"{SITE_URL}/rss/podcast_{mode}.xml", rel="self")
    fg.podcast.itunes_category("Business", "Investing")
    fg.podcast.itunes_image(COVER_URL)
    fg.podcast.itunes_explicit("no")
    fg.podcast.itunes_author("幫幫忙AI投資腦")
    fg.podcast.itunes_owner(name="幫幫忙AI投資腦", email="tim.oneway@gmail.com")

    # ===== 選資料夾（只處理對應模式）=====
    episodes_dir = "docs/podcast"
    folder = pick_folder_by_mode(mode)
    base_path = os.path.join(episodes_dir, folder)
    audio_path = os.path.join(base_path, "audio.mp3")
    summary_path = os.path.join(base_path, "summary.txt")

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"⚠️ 找不到 audio.mp3：{audio_path}")

    # ===== 產生音檔連結 =====
    audio_url = build_audio_url(base_path, folder)

    # ===== 讀取 mp3 長度 =====
    try:
        mp3 = MP3(audio_path)
        duration = int(mp3.info.length)
    except Exception as e:
        logger.warning(f"⚠️ 讀取 mp3 時長失敗：{e}")
        duration = None

    # ===== 標題與發布時間（台北時間）=====
    tz = pytz.timezone("Asia/Taipei")
    folder_date_str = folder.split("_")[0]  # YYYYMMDD
    pub_date = tz.localize(datetime.datetime.strptime(folder_date_str, "%Y%m%d"))
    title = f"幫幫忙每日投資快報 - {'台股' if mode == 'tw' else '美股'}（{folder_date_str}）"

    # ===== 內容描述 =====
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            summary_text = f.read().strip()
        full_description = f"{FIXED_DESCRIPTION}\n\n🎯 今日摘要：\n{summary_text}"
    else:
        logger.info("ℹ️ 找不到 summary.txt，使用預設描述")
        full_description = FIXED_DESCRIPTION

    # ===== Feed Entry =====
    fe = fg.add_entry()
    fe.id(audio_url)
    fe.title(title)
    fe.description(full_description)
    fe.content(full_description, type="CDATA")
    fe.enclosure(audio_url, str(os.path.getsize(audio_path)), "audio/mpeg")
    fe.pubDate(pub_date)
    if duration:
        fe.podcast.itunes_duration(str(datetime.timedelta(seconds=duration)))

    # ===== 輸出 RSS =====
    rss_file = f"docs/rss/podcast_{mode}.xml"
    os.makedirs(os.path.dirname(rss_file), exist_ok=True)
    fg.rss_file(rss_file)
    logger.info(f"✅ 已產生 RSS：{rss_file}（mode={mode}, folder={folder}）")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Feed Publisher")
    parser.add_argument("--mode", default=os.getenv("PODCAST_MODE", "tw"), choices=["tw", "us"])
    args = parser.parse_args()
    generate_rss(args.mode.lower())