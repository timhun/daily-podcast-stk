# scripts/utils_podcast.py
import datetime
import pytz

def is_weekend_tw():
    tz = pytz.timezone("Asia/Taipei")
    weekday = datetime.datetime.now(tz).weekday()
    return weekday in [5, 6]  # 週六週日

def load_prompt_template(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()