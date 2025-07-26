import requests
import pandas as pd
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import pytz

# ====== 基本設定 ======
logger = logging.getLogger(__name__)
TW_TZ = pytz.timezone("Asia/Taipei")

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
    """
    民國年月日轉西元日期，例如 '1140725' → 2025-07-25
    """
    if len(roc_yyyymmdd) != 7:
        raise ValueError(f"ROC 日期格式不正確：{roc_yyyymmdd}")
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

# ====== 主要函式：從 TWSE OpenAPI 擷取加權指數 ======

def fetch_taiex_from_twse_latest(date_ymd: str | None = None, session: requests.Session | None = None) -> pd.DataFrame | None:
    """
    從 TWSE OpenAPI 擷取最新「發行量加權股價指數」資料。
    API: https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX?date=YYYYMMDD
    """
    date_ymd = date_ymd or _today_tw_ymd()
    session = session or _build_retry_session()
    url = f"https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX?date={date_ymd}"

    try:
        resp = session.get(url, timeout=10)
        if resp.status_code != 200:
            logger.error(f"❌ TWSE OpenAPI 回應非 200: {resp.status_code} - {resp.text[:200]}")
            return None

        data = resp.json()
        if not isinstance(data, list):
            logger.error(f"❌ TWSE OpenAPI 回傳格式錯誤：{type(data)}")
            return None

        # 找加權指數項目
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
        logger.exception(f"❌ TWSE OpenAPI 擷取失敗: {e}")
        return None

# ====== 外部存取介面 ======

def get_latest_taiex_summary() -> pd.DataFrame | None:
    """
    回傳加權指數的最新資料 DataFrame。
    fallback 可加上 Yahoo Finance 或 Goodinfo 等邏輯。
    """
    df = fetch_taiex_from_twse_latest()
    if df is not None and not df.empty:
        return df

    logger.warning("⚠️ fallback：尚未實作 Yahoo Finance / Goodinfo 備援")
    return None

# ====== 測試區 ======

if __name__ == "__main__":
    df = get_latest_taiex_summary()
    if df is not None:
        print(df)
    else:
        print("❌ 無法取得加權指數資料")