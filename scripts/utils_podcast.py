# scripts/utils_podcast.py

import logging
import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pytz


# ====== 設定 ======
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
TW_TZ = pytz.timezone("Asia/Taipei")

# ====== Podcast 用工具 ======

def get_podcast_mode() -> str:
    return os.getenv("PODCAST_MODE", "tw").lower()

def get_today_display() -> str:
    return datetime.now(TW_TZ).strftime("%Y年%m月%d日")

def is_weekend_prompt(mode: str, now: datetime | None = None) -> bool:
    now = now or datetime.now(TW_TZ)
    if mode == "tw":
        return now.weekday() in (5, 6)
    elif mode == "us":
        return now.weekday() in (6, 0)
    return False

def is_trading_day_taiwan(now: datetime | None = None) -> bool:
    now = now or datetime.now(TW_TZ)
    return now.weekday() < 5 and now.hour >= 14

# ====== 工具函式 ======

def _today_tw_ymd() -> str:
    return datetime.now(TW_TZ).strftime("%Y%m%d")

def _safe_float(x, default=None):
    if x is None or x == "" or x == "--":
        return default
    try:
        return float(str(x).replace(",", "").replace("%", ""))
    except Exception:
        return default

def _roc_to_gregorian(roc_yyyymmdd: str) -> datetime.date:
    roc_year = int(roc_yyyymmdd[:3])
    month = int(roc_yyyymmdd[3:5])
    day = int(roc_yyyymmdd[5:7])
    return datetime(roc_year + 1911, month, day).date()

def _build_retry_session(total=3, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504)) -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.headers.update({"User-Agent": "utils_podcast/1.0"})
    return s

# ====== 法人買賣超 (WantGoo) ======

def get_institutional_trading_wantgoo() -> dict:
    url = "https://www.wantgoo.com/stock/institutional-investors/three-trade-for-trading-amount"
    session = _build_retry_session()
    try:
        res = session.get(url, timeout=10)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table", class_="wg-table")
        if not table:
            raise ValueError("找不到法人表格")

        data = {}
        for row in table.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) >= 3:
                label = tds[0].get_text(strip=True)
                value = _safe_float(tds[1].get_text(strip=True))
                if "外資" in label:
                    data["foreign"] = value
                elif "投信" in label:
                    data["investment"] = value
                elif "自營商" in label:
                    data["dealer"] = value

        if all(k in data for k in ("foreign", "investment", "dealer")):
            data["total_netbuy"] = sum([data["foreign"], data["investment"], data["dealer"]])
            logger.info(f"✅ 法人買賣超：{data}")
            return data
        logger.warning(f"⚠️ 法人資料不完整：{data}")
        return {}
    except Exception as e:
        logger.warning(f"⚠️ 擷取法人買賣超失敗：{e}")
        return {}

# ====== TAIEX 資料主流程 ======

def get_latest_taiex_summary() -> pd.DataFrame | None:
    try:
        ticker = "^TWII"
        df = yf.download(ticker, period="90d", interval="1d", progress=False, auto_adjust=False)
        if df.empty or len(df) < 60:
            raise ValueError("資料不足")

        df["ma5"] = df["Close"].rolling(5).mean()
        df["ma10"] = df["Close"].rolling(10).mean()
        df["ma20"] = df["Close"].rolling(20).mean()
        df["ma60"] = df["Close"].rolling(60).mean()
        ema12 = df["Close"].ewm(span=12, adjust=False).mean()
        ema26 = df["Close"].ewm(span=26, adjust=False).mean()
        df["macd"] = ema12 - ema26

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        close = latest["Close"].item() if hasattr(latest["Close"], "item") else float(latest["Close"])
        prev_close = prev["Close"].item() if hasattr(prev["Close"], "item") else float(prev["Close"])

        change = close - prev_close
        change_pct = round(change / prev_close * 100, 2)

        volume = latest["Volume"].item() if hasattr(latest["Volume"], "item") else float(latest["Volume"])
        volume_in_lots = volume / 1000 if volume else None
        volume_billion_ntd = round(volume_in_lots * close / 10000) if volume_in_lots else None

        data = {
            "date": latest.name.date(),
            "close": close,
            "change": change,
            "change_pct": change_pct,
            "volume": volume,
            "volume_billion": volume_billion_ntd,
            "ma5": float(latest["ma5"]),
            "ma10": float(latest["ma10"]),
            "ma20": float(latest["ma20"]),
            "ma60": float(latest["ma60"]),
            "macd": float(latest["macd"]),
            "source": "YahooFinance"
        }

        # 整合法人資料
        inst = get_institutional_trading_wantgoo()
        data.update(inst)

        logger.info(f"✅ TAIEX 加權指數資料整合：{data}")
        return pd.DataFrame([data])

    except Exception as e:
        logger.warning(f"⚠️ Yahoo Finance 擷取失敗：{e}")
        return None
