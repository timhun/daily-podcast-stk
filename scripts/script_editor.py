# scripts/script_editor.py
import os
import re
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import List

import pandas as pd
import feedparser

from .grok_api import suggest_params

LOG_DIR = "logs"
OUT_ROOT = "docs/podcast"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("script_editor")
logger.setLevel(logging.INFO)
fh = RotatingFileHandler(os.path.join(LOG_DIR, "script_editor.log"), maxBytes=1_000_000, backupCount=2, encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(fh)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(sh)

def _news(limit=3) -> List[str]:
    url = "https://tw.stock.yahoo.com/rss?category=news"
    d = feedparser.parse(url)
    items = []
    for e in d.entries:
        title = e.get("title","")
        link = e.get("link","")
        if ("經濟" in title) or ("半導體" in title):
            items.append(f"{title} | {link}")
        if len(items) >= limit:
            break
    if not items:
        # 若沒匹配，退而求其次取前 3
        items = [f"{e.get('title','')} | {e.get('link','')}" for e in d.entries[:limit]]
    return items

def generate_script(mode: str, symbol: str, strategy_json_path: str) -> str:
    today = datetime.now().strftime("%Y%m%d")
    out_dir = os.path.join(OUT_ROOT, f"{today}_{mode}")
    os.makedirs(out_dir, exist_ok=True)
    # 讀策略摘要
    if os.path.exists(strategy_json_path):
        import json
        with open(strategy_json_path, "r", encoding="utf-8") as f:
            strat = json.load(f)
    else:
        strat = {"winner":"N/A","winner_return":0,"baseline_return":0,"signal":"hold","price":None}

    news = _news(limit=3)
    llm_tip = suggest_params(strat)

    txt = []
    txt.append(f"")
    txt.append(f"標的：{symbol}")
    txt.append(f"最優策略：{strat.get('winner')} 報酬={strat.get('winner_return'):.2%} 基準={strat.get('baseline_return'):.2%}")
    txt.append(f"即時訊號：{strat.get('signal')} 價格={strat.get('price')}")
    txt.append("—")
    txt.append("今日焦點新聞（優先《經濟》《半導體》）：")
    for i, n in enumerate(news, 1):
        txt.append(f"{i}. {n}")
    txt.append("—")
    txt.append(f"Grok 建議（stub）: {llm_tip}")

    out_path = os.path.join(out_dir, "script.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt))
    logger.info(f"已產出稿件：{out_path}")
    return out_path