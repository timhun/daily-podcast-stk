# scripts/utils_podcast_tw.py

import os
import pytz
from datetime import datetime

from workalendar.asia import Taiwan

# 台灣時區
TW_TZ = pytz.timezone("Asia/Taipei")


def get_today_tw() -> datetime:
    """
    回傳台灣當地時間的現在 datetime（含時區）
    """
    return datetime.now(TW_TZ)


def get_today_tw_ymd_str() -> str:
    """
    回傳今天日期（台灣時區）字串：YYYYMMDD，例如 20250729
    """
    return get_today_tw().strftime("%Y%m%d")


def is_weekend_tw(date: datetime = None) -> bool:
    """
    判斷指定日期（預設為今天）是否為週末（六日）
    """
    target = date or get_today_tw()
    return target.weekday() in (5, 6)  # 5 = Saturday, 6 = Sunday


def is_tw_holiday(date: datetime = None) -> bool:
    """
    判斷指定日期（預設為今天）是否為台灣國定假日或補假日（非工作日）
    使用 workalendar 套件
    """
    cal = Taiwan()
    target = (date or get_today_tw()).date()
    return not cal.is_working_day(target)


def load_prompt_template(file_path: str) -> str:
    """
    載入指定 prompt 模板文字內容
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ 找不到 Prompt 檔案：{file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
