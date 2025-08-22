# scripts/script_editor.py
import os, json, logging, argparse, requests, pytz
from datetime import datetime
from bs4 import BeautifulSoup

os.makedirs("logs", exist_ok=True)
logging.basicConfig(filename="logs/script_editor.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("editor")

def load_cfg():
    return json.load(open("config.json","r",encoding="utf-8"))

def taipei_now():
    tz = pytz.timezone("Asia/Taipei")
    return datetime.now(tz).strftime("%Y%m%d")

def fetch_rss_items(urls, limit=3, keyword_filters=None):
    items=[]
    for url in urls:
        try:
            r = requests.get(url, timeout=15)
            soup = BeautifulSoup(r.text, "xml")
            for it in soup.find_all("item")[:10]:
                title = it.title.text if it.title else ""
                link  = it.link.text if it.link else ""
                desc  = it.description.text if it.description else ""
                if keyword_filters:
                    if not any(k in (title+desc) for k in keyword_filters): 
                        continue
                items.append({"title":title, "link":link, "desc":desc})
        except Exception as e:
            logger.error(f"RSS fail: {url} {e}")
    return items[:limit]

def read_json(path):
    return json.load(open(path,"r",encoding="utf-8")) if os.path.exists(path) else None

def call_llm(model, api_key, sys_prompt, user_prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://timhun.github.io",
        "X-Title": "daily-podcast-stk"
    }
    payload = {
        "model": model,
        "messages": [
            {"role":"system","content":sys_prompt},
            {"role":"user","content":user_prompt}
        ],
        "temperature": 0.6
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def build_prompt(mode, cfg):
    date_str = taipei_now()
    if mode=="us":
        # 指數/ETF價格來自 collector
        dji  = read_json_path_csv("data/daily__DJI.csv", "^DJI")
        ixic = read_json_path_csv("data/daily__IXIC.csv", "^IXIC")
        gspc = read_json_path_csv("data/daily__GSPC.csv", "^GSPC")
        sox  = read_json_path_csv("data/daily__SOX.csv", "^SOX") if os.path.exists("data/daily__SOX.csv") else None
        qqq  = read_last("data/daily_QQQ.csv")
        spy  = read_last("data/daily_SPY.csv")
        ibit = read_last("data/daily_IBIT.csv") if os.path.exists("data/daily_IBIT.csv") else None
        btc  = read_last("data/daily_BTC-USD.csv")
        gold = read_last("data/daily_GC_F.csv")
        tnx  = read_last("data/daily__TNX.csv") if os.path.exists("data/daily__TNX.csv") else None

        a_qqq = read_json("data/market_analysis_QQQ.json")
        rss_items = fetch_rss_items(cfg["rss"]["us"], limit=3, keyword_filters=None)

        user = f"""
今天是台北時間 {date_str} 早上，美股盤後播報。
請用台灣慣用語，語速1.3倍口吻，主持人：幫幫忙；節目：幫幫忙說台股（美股特輯）。
內容要求（純正文、繁體中文）：
1. 大盤收盤：道瓊(^DJI)、Nasdaq(^IXIC)、S&P500(^GSPC)、費半(^SOX) 點位與漲跌幅（依我提供的資料）。
2. QQQ、SPY、IBIT、比特幣(BTC)、黃金(Gold) 最新；十年期美債(^TNX) 殖利率。
3. 深入 QQQ：根據分析與策略，給短線交易建議與買賣訊號（整合資料）。
4. 結尾給一則 Andre Kostolany 投資名言。
資料：
DJI={dji}, IXIC={ixic}, GSPC={gspc}, SOX={sox}
QQQ={qqq}, SPY={spy}, IBIT={ibit}, BTC={btc}, GOLD={gold}, TNX={tnx}
QQQ分析={a_qqq}
美股或AI新聞（摘要3則）：{rss_items}
僅輸出逐字稿正文，不要任何說明或JSON。
"""
    else:
        twii = read_last("data/daily__TWII.csv")
        tw50 = read_last("data/daily_0050_TW.csv")
        a_0050 = read_json("data/market_analysis_0050_TW.json")
        rss_items = fetch_rss_items(cfg["rss"]["tw"], limit=3, keyword_filters=["經濟","半導體","AI","科技"])

        user = f"""
今天是台北時間 {date_str} 下午，台股盤後播報。
請用台灣慣用語，語速1.3倍口吻，主持人：幫幫忙；節目：幫幫忙說台股。
內容要求（純正文、繁體中文）：
1. 台股加權(^TWII) 收盤與漲跌幅；2. 0050(元大台灣50) 收盤。
3. 深入 0050：根據策略與分析，給短線交易建議與訊號。
4. 三則重點新聞（附一句話重點）。
5. 結尾給一則 Andre Kostolany 投資名言。
資料：
TWII={twii}, 0050={tw50}
0050分析={a_0050}
台股新聞（摘要3則）：{rss_items}
僅輸出逐字稿正文，不要任何說明或JSON。
"""
    return user

def read_last(path):
    import pandas as pd
    if not os.path.exists(path): return None
    df = pd.read_csv(path)
    if df.empty: return None
    row = df.iloc[-1].to_dict()
    return {k:(float(v) if k in ["Open","High","Low","Close","Adj Close","Volume"] else v) for k,v in row.items()}

def read_json_path_csv(path, label):
    # 這裡僅做存在標記，實務上可讀值；為簡化只返回檔名存在狀態
    return {"symbol": label, "csv": os.path.exists(path)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["us","tw"], required=True)
    args = parser.parse_args()

    cfg = load_cfg()
    date_str = taipei_now()
    out_dir = f"docs/podcast/{date_str}_{args.mode}"
    os.makedirs(out_dir, exist_ok=True)

    model = cfg["llm"]["model"]
    api_key = os.environ.get("OPENROUTER_API_KEY","")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY missing")

    sys_prompt = "你是一位親切自然的台灣專業投資播報員，語氣口語、節奏偏快(1.3x)，重點清楚，避免行話。"
    user_prompt = build_prompt(args.mode, cfg)
    text = call_llm(model, api_key, sys_prompt, user_prompt)

    with open(f"{out_dir}/script.txt","w",encoding="utf-8") as f:
        f.write(text)
    logger.info(f"script generated -> {out_dir}/script.txt")

if __name__=="__main__":
    main()
