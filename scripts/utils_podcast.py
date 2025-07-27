import os
import logging
import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pytz
import yfinance as yf

# ====== 設定 ======
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
TW_TZ = pytz.timezone("Asia/Taipei")

# ====== Podcast 用工具 ======

def get_podcast_mode() -> str:
    return os.getenv("PODCAST_MODE", "tw").lower()


def get_today_display() -> str:
    """返回台灣當地日期字串，例：2025年07月27日"""
    return datetime.now(TW_TZ).strftime("%Y年%m月%d日")


def is_weekend_prompt(mode: str, now: datetime | None = None) -> bool:
    now = now or datetime.now(TW_TZ)
    if mode == "tw":
        return now.weekday() in (5, 6)  # 六日
    elif mode == "us":
        return now.weekday() in (6, 0)  # 日、一（以台灣時間為準）
    return False


def is_trading_day_taiwan(now: datetime | None = None) -> bool:
    now = now or datetime.now(TW_TZ)
    if now.weekday() >= 5:
        return False  # 六日
    if now.hour < 14:
        return False  # 尚未收盤
    return True

# ====== 台股資料工具（原 utils_tw_data 整合） ======

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
    s.headers.update({"User-Agent": "utils_tw_data/1.0 (TWSE OpenAPI fetcher)"})
    return s


def get_goodinfo_taiex_summary() -> dict | None:
    url = "https://goodinfo.tw/tw/StockIdxDetail.asp?STOCK_ID=加權指數"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://goodinfo.tw/"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table", class_="solid_1_padding_4_0_tbl")
        if not table:
            logger.warning("⚠️ 找不到 Goodinfo 均線表格")
            return None
        result = {}
        for row in table.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) < 6:
                continue
            label = tds[0].get_text(strip=True)
            ma_text = tds[5].get_text(strip=True).replace("↗", "").replace("↘", "")
            value = _safe_float(ma_text)
            if label == "5日":
                result["ma5"] = value
            elif label == "10日":
                result["ma10"] = value
            elif label == "月":
                result["ma20"] = value
            elif label == "季":
                result["ma60"] = value
        if all(k in result for k in ("ma5", "ma10", "ma20", "ma60")):
            logger.info(f"✅ Goodinfo 均線資料: {result}")
            return result
        logger.warning(f"⚠️ Goodinfo 資料不完整: {result}")
        return None
    except Exception as e:
        logger.exception(f"❌ 擷取 Goodinfo 均線失敗: {e}")
        return None


def fetch_taiex_from_twse_latest(date_ymd: str | None = None, session: requests.Session | None = None) -> pd.DataFrame | None:
    date_ymd = date_ymd or _today_tw_ymd()
    session = session or _build_retry_session()
    url = f"https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX?date={date_ymd}"
    try:
        resp = session.get(url, timeout=10)
        if resp.status_code != 200:
            logger.error(f"❌ TWSE 回應非 200: {resp.status_code} - {resp.text[:200]}")
            return None
        data = resp.json()
        target = next((item for item in data if item.get("指數") == "發行量加權股價指數"), None)
        if not target:
            logger.error("❌ 找不到『發行量加權股價指數』欄位")
            return None
        roc_date_str = target.get("日期")
        close = _safe_float(target.get("收盤指數"))
        chg_sign = target.get("漲跌")
        chg_pts = _safe_float(target.get("漲跌點數"), default=0.0)
        if chg_sign == "-":
            chg_pts = -abs(chg_pts)
        elif chg_sign == "+":
            chg_pts = abs(chg_pts)
        chg_pct = _safe_float(target.get("漲跌百分比"), default=0.0)
        date_gregorian = _roc_to_gregorian(roc_date_str)
        df = pd.DataFrame([{
            "date": date_gregorian,
            "close": close,
            "change": chg_pts,
            "change_pct": chg_pct,
            "source": "TWSE_OPENAPI",
            "raw": target
        }])
        logger.info(f"✅ TWSE 加權指數：{df.iloc[0].to_dict()}")
        return df
    except Exception as e:
        logger.exception(f"❌ TWSE 擷取失敗: {e}")
        return None


def get_latest_taiex_summary() -> pd.DataFrame | None:
    try:
        ticker = "^TWII"
        df = yf.download(ticker, period="90d", interval="1d", progress=False)
        if df.empty or len(df) < 60:
            raise ValueError("資料不足")
        df["ma5"] = df["Close"].rolling(5).mean()
        df["ma10"] = df["Close"].rolling(10).mean()
        df["ma20"] = df["Close"].rolling(20).mean()
        df["ma60"] = df["Close"].rolling(60).mean()

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        change = float(latest["Close"] - prev["Close"])
        change_pct = round(change / prev["Close"] * 100, 2)
        volume = float(latest["Volume"]) if not pd.isna(latest["Volume"]) else None
        volume_ntd = round(volume / 1e8, 2) if volume else None  # 換算為新台幣百億元單位

        result = pd.DataFrame([{
            "date": latest.name.date(),
            "close": float(latest["Close"]),
            "change": change,
            "change_pct": change_pct,
            "volume": volume,
            "volume_ntd": volume_ntd,
            "ma5": float(latest["ma5"]),
            "ma10": float(latest["ma10"]),
            "ma20": float(latest["ma20"]),
            "ma60": float(latest["ma60"]),
            "source": "YahooFinance"
        }])
        logger.info(f"✅ Yahoo 加權指數：{result.iloc[0].to_dict()}")
        return result
    except Exception as e:
        logger.warning(f"⚠️ Yahoo Finance 失敗，改用 TWSE 備援：{e}")
        df = fetch_taiex_from_twse_latest()
        if df is not None and not df.empty:
            goodinfo = get_goodinfo_taiex_summary()
            if goodinfo:
                for k, v in goodinfo.items():
                    df[k] = v
            return df
        return None
