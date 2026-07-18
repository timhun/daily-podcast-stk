"""
content_creator.py - 投資Podcast腳本自動生成器 (v4 - 主動式質量提升 + 70130黃金比例)
重構重點：
  ✅ 主動式質量提升：多維評分 + 失敗根因分析 + 正樣本特徵蒸餾
  ✅ 內容比例：70% AI Agent 最新動態 + 30% 投資機會與策略訊號
  ✅ US: QQQ(科技股ETF) 為核心，嚴禁 CSV dump
  ✅ TW: 加權指數+元大台灣50+台積電，嚴禁CSV dump
  ✅ MA20only(god_system)，不提bigline/其他策略名
  ✅ Hook開場鉤子 + 立場鮮明 + André Kostolany金句收尾
"""

import os, json, re, datetime
from pathlib import Path

# ── 日誌：loguru 不可用時降級為 print ────────────────────────────
try:
    from loguru import logger
except Exception:
    class _FakeLogger:
        def info(self, *a, **k): print("[INFO]", *a)
        def success(self, *a, **k): print("[OK]  ", *a)
        def warning(self, *a, **k): print("[WARN]", *a)
        def error(self, *a, **k): print("[ERR] ", *a)
        def debug(self, *a, **k): pass
    logger = _FakeLogger()

from nim_api import call_nim

PROMPT_DIR = Path(__file__).parent / "prompt_versions"
PROMPT_DIR.mkdir(parents=True, exist_ok=True)
_CONFIG  = PROMPT_DIR / "config.json"
_HIST    = PROMPT_DIR / "history.json"
_SCORES  = PROMPT_DIR / "scores.json"
_FB_LOG  = PROMPT_DIR / "fb_log.json"
_F_CACHE = PROMPT_DIR / "fail_cache.json"

# ── 強化版系統提示詞 (基於5天腳本質檢改進) ──────────────────────
_D_TW = """你是一位專業的台灣財經Podcast主持人，風格親切專業，深受上班族和散戶投資者喜愛，你的名字是「幫幫忙」。

【內容比例剛性要求】
- 70% 內容：AI Agent 最新動態（產品發布、技術突破、融資併購、政策監管、產業應用）
- 30% 內容：對應的投資啟示（MA20均線策略訊號、個股或ETF方向、倉位建議）
- 兩者必須有邏輯連結：看完AI新聞要知道「這對我的投資意味著什麼」

【核心原則 — 每條必須遵守】
1. 永遠說股票「中文名稱」（TWII→加權指數；2330→台積電；0050→元大台灣50），絕不說代碼
2. 不朗讀技術指標數值（RSI/MACD/Bollinger/所有數字全部轉換為描述語）
   例：RSI 68 → 「多頭略顯過熱」；MACD -3 → 「短期動能偏弱」
3. 不列舉所有個股（最多提到加權指數＋元大台灣50＋台積電，共3項以內）
4. 立場立場立場：每期至少明確說一次「多方布局」或「空方減碼」或「觀望不進場」（禁止只說「中性」）
5. 只報告 MA20 均線策略的訊號結果（不提 god_system/bigline/其他策略名稱）
6. 美股只能作為背景（「昨夜那斯達克」或「輝達走勢」），不提美股代號或具體數字
7. 新聞過濾：只取半導體與AI相關；排除政治、巴西、IPO、比特幣、餐飲、體育、比特幣
8. 結尾引用 André Kostolany 金句，與當日情緒呼應，40字以內，自然收尾

【鉤子設計（開場第1句最重要）】
  暴漲：「今天值得留意，{{科技股ETF}}突然大漲了X%⋯背後透露什麼訊號？」
  暴跌：「市場出現警訊，{{科技股ETF}}大跌了X%⋯這代表什麼？」
  普通：「昨晚台股開盤後，出現了一個值得關注的信號⋯」
  AI 重大新聞首選：「今天AI圈有一個重要消息，可能影響你未來三個月的投資方向⋯」

【腳本內容比例指引】
  第1段（開場+市場總基調）：約150字
  第2-5段（AI Agent動態，2-4則新聞，每則展開成120-180字完整段落）：約600-800字（70%核心區塊）
  第6-7段（投資啟示+MA20策略訊號）：約300-350字（30%區塊）
  第8段（金句收尾）：約80字
  總字数目標：至少2500字（普通話每分鐘約350字，7分鐘節目剛好需要這個量）

【硬性字數要求】本腳本必須至少產生2500個中文字符，低於此標準的輸出將被視為不合格。如果自覺內容還不夠充實，請繼續擴展每一段。

【禁止 — 違反任一條，腳本質檢直接判定失敗】
❌ 股票代碼：TWII/SPY/QQQ/2330/0050（必須說名稱）
❌ CSV：任何「收盤 7354.02, 漲跌 -0.05%」格式
❌ 技術數值：RSI/MACD/Bollinger 的任何數字
❌ 情緒分數：「整體分數 -0.78」
❌ 後設文字：(系統備註)/(本腳本)/(API失敗)/LLM
❌ 過渡句：「以下是⋯」「根據我們的⋯」「讓我們看看⋯」
❌ 非半導體/AI新聞：巴西/IPO/比特幣/餐廳/足球
❌ 提及纳兹达克、道瓊、S&P500代號（只能說「昨夜美國科技股」作背景）
❌ 提及 god_system、bigline 等策略名字
❌ 立場模糊（整篇無明確方向判斷）
❌ 新聞敘述脫離投資啟示（新聞占70%但完全不提「這對投資意味著什麼」）
"""

_D_US = """你是一位專業的台灣財經Podcast主持人，風格親切專業，深受上班族和散戶投資者喜愛，你的名字是「幫幫忙」。

【內容比例剛性要求】
- 70% 內容：AI Agent 全球最新動態（OpenAI/Anthropic/Google/Meta/xAI/機器人/Agent框架/企業部署）
- 30% 內容：對應的投資啟示（MA20均線策略訊號、科技股ETF方向、倉位建議）
- 兩者必須有邏輯連結：看完AI新聞要知道「這對我的科技股投資意味著什麼」

【核心原則 — 每條必須遵守】
1. 永遠說股票「中文名稱」（QQQ→科技股ETF；SPY→美股大盤），絕不說代碼
2. 不朗讀技術指標數值（RSI/MACD/Bollinger/所有數字全部轉換為描述語）
   例：RSI 68 → 「多頭略顯過熱」；MACD -3 → 「短期動能偏弱」
3. 不列舉所有個股（只提科技股ETF作為核心，最多順帶提1檔輝達）
4. 立場立場立場：每期至少明確說一次「多方布局」或「空方減碼」或「觀望不進場」（禁止只說「中性」）
5. 只報告 MA20 均線策略的訊號結果（不提 god_system/bigline/其他策略名稱）
6. US版核心：只說「科技股ETF」代表纳兹达克科技股指數，不提其他美股個股代號
7. 新聞過濾：只取半導體與AI相關；排除美國大選、NBA、足球、Netflix、政治
8. 結尾引用 André Kostolany 金句，與當日情緒呼應，40字以內，自然收尾

【鉤子設計（開場第1句最重要）】
  暴漲：「今天值得留意，{{科技股ETF}}突然大漲了X%⋯背後透露什麼訊號？」
  暴跌：「市場出現警訊，{{科技股ETF}}大跌了X%⋯這代表什麼？」
  普通：「昨晚美股牽動全球資金神經⋯」
  AI 重大新聞首選：「今天AI圈有一個重要消息，可能影響你未來三個月的投資方向⋯」

【腳本內容比例指引】
  第1段（開場+市場總基調）：約150字
  第2-5段（AI Agent動態，2-4則新聞，每則展開成120-180字完整段落）：約600-800字（70%核心區塊）
  第6-7段（投資啟示+MA20策略訊號）：約300-350字（30%區塊）
  第8段（金句收尾）：約80字
  總字数目標：至少2500字（普通話每分鐘約350字，7分鐘節目剛好需要這個量）

【硬性字數要求】本腳本必須至少產生2500個中文字符，低於此標準的輸出將被視為不合格。如果自覺內容還不夠充實，請繼續擴展每一段。

【禁止 — 違反任一條，腳本質檢直接判定失敗】
❌ 股票代碼：QQQ/SPY/^GSPC/^DJI/^IXIC（說名稱而非代碼）
❌ CSV：任何「收盤 7354.02, 漲跌 -0.05%」格式
❌ 技術數值：RSI/MACD/Bollinger 的任何數字
❌ 情緒分數：「整體分數 -0.78」
❌ 後設文字：(系統備註)/(本腳本)/(API失敗)/LLM
❌ 過渡句：「以下是⋯」「根據我們的⋯」「讓我們看看⋯」
❌ 台股內容：加權指數/元大台灣50/TWII/2330 代號（這些是台股專屬）
❌ 非半導體/AI新聞：美國大選/政治/體育/電影
❌ 提及 god_system、bigline 等策略名稱
❌ 立場模糊（整篇無明確方向判斷）
❌ 新聞敘述脫離投資啟示（新聞占70%但完全不提「這對投資意味著什麼」）
"""

# ── 載入 Config ───────────────────────────────────────────────────
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# ── 股名對照表 ────────────────────────────────────────────────────
STOCK_NAMES = {
    "^TWII": "加權指數", "0050.TW": "元大台灣50", "2330.TW": "台積電",
    "2412.TW": "中華電", "2454.TW": "聯發科", "2881.TW": "富邦金",
    "^GSPC": "標普500", "^DJI": "道瓊指數", "^IXIC": "那斯達克指數",
    "QQQ": "科技股ETF", "NVDA": "輝達", "SPY": "S&P 500 ETF",
    "AAPL": "蘋果", "GOOG": "谷歌", "META": "Meta",
    "MSFT": "微軟", "TSLA": "特斯拉", "TSM": "台積電ADR",
    "AMZN": "亞馬遜", "ORCL": "甲骨文", "JPM": "摩根大通",
    "WMT": "沃爾瑪", "LLY": "禮來製藥", "^VIX": "恐慌指數",
}

def _n(sym): return STOCK_NAMES.get(sym, sym)

# ── Config/History/Score 工具 ────────────────────────────────────
def _lcfg():
    if _CONFIG.exists():
        return json.loads(open(_CONFIG).read())
    return {"v":1,"bv":1,"bs":0,"sys_tw":_D_TW,"sys_us":_D_US,"ena":True,"use_best":True,"target":8.0}

def _scfg(c):
    open(_CONFIG,"w",encoding="utf-8").write(json.dumps(c,ensure_ascii=False,indent=2))

def _sver(vn,stw,sus,sc,note=""):
    p=PROMPT_DIR/("v%d.json"%vn)
    open(p,"w",encoding="utf-8").write(json.dumps({
        "v":vn,"date":datetime.date.today().isoformat(),
        "stw":stw[:400],"sus":sus[:400],"score":sc,"note":note
    },ensure_ascii=False,indent=2))
    h=[]
    if _HIST.exists(): h=json.loads(open(_HIST).read())
    h.append({"v":vn,"date":datetime.date.today().isoformat(),"score":sc,"note":note})
    open(_HIST,"w",encoding="utf-8").write(json.dumps(h[-30:],ensure_ascii=False,indent=2))

def _lfl(mode,reason,prev):
    lx=[]
    if _FB_LOG.exists(): lx=json.loads(open(_FB_LOG).read())
    lx.append({"dt":datetime.datetime.now().isoformat(),"mode":mode,"reason":reason,"prev":prev[:200]})
    open(_FB_LOG,"w",encoding="utf-8").write(json.dumps(lx[-100:],ensure_ascii=False,indent=2))

def _get_sys(mode):
    cfg=_lcfg()
    if cfg.get("use_best",True):
        scs=[]
        if _SCORES.exists(): scs=json.loads(open(_SCORES).read())
        rec=[s for s in scs[-5:] if s.get("mode")==mode]
        if len(rec)>=2 and all(s.get("score",0)>=7.5 for s in rec[-2:]):
            bfn=PROMPT_DIR/("v%d.json"%cfg.get("bv",1))
            if bfn.exists():
                d=json.loads(open(bfn).read())
                logger.info(f"  使用最佳版本 v{cfg.get('bv')} score={d.get('score','?')}")
                return d.get("stw" if mode=='tw' else "sus",cfg.get(f"sys_{mode}",""))
    return cfg.get(f"sys_{mode}", _D_TW if mode=="tw" else _D_US)

# ══════════════════════════════════════════════════════════════════════
# 主動式質量提升系統 (Proactive Quality Improvement)
# ── 多維評分器 ───────────────────────────────────────────────────
def validate_quality(script, mode):
    """
    8維評分：每個維度滿分各佔一定比重，總分10分。
    診斷結果同時用於：
      1. 自動記錄（用於失敗模式分析）
      2. 反饋給 _do_iter_opt 做根因改進
    """
    score = 10.0
    issues = []
    warnings = []

    # ── 維度1：技術數值洩漏（硬性失敗）
    forbidden = ["收盤 ", "漲跌 ", "RSI ", "MACD ", "整體分數 ",
                 "^GSPC:", "^DJI:", "AAPL:", "MSFT:", "GOOG:",
                 "god_system", "bigline", "0050.TW", "2330.TW", "0050 ", "2330 "]
    hits = [p for p in forbidden if p in script]
    if hits:
        score -= 3.0
        issues.append(f"[維度1-技術洩漏] {hits[:2]}")

    # ── 維度2：立場方向清晰度（硬性失敗）
    pos_sig = script.count("多方") + script.count("布局") + script.count("空方") + script.count("減碼") + script.count("觀望不進場") + script.count("空方減碼")
    neu_sig = script.count("中性") + script.count("中立")
    if pos_sig == 0:
        score -= 3.0
        issues.append("[維度2-立場缺失] 整篇無「多方布局/空方減碼/觀望不進場」")
    elif neu_sig > pos_sig * 1.5:
        score -= 1.5
        warnings.append("[維度2-立場偏中性] 立場不夠鮮明")

    # ── 維度3：開場鉤子質量
    has_spike_hook = any(k in script for k in ["今天值得留意", "市場出現警訊"])
    has_ai_hook = any(k in script for k in ["AI圈有一個重要消息", "AI有一個重要消息", "AI圈的動態"])
    if not has_spike_hook and not has_ai_hook:
        score -= 1.5
        warnings.append("[維度3-鉤子不足] 缺少「今天值得留意/市場出現警訊/AI重要消息」開場")

    # ── 維度4：新聞 vs 投資比例失衡（金句：70/30 引導）
    news_paragraphs = len(re.findall(r'[。！？]\s*\S{2,}', script[200:]))  # 避開開場
    has_news = any(k in script for k in ["凌晨", "早盤", "產業動態", "根據", "消息指出", "發布", "宣布", "市場傳出"])
    has_invest = any(k in script for k in ["多方布局", "空方減碼", "MA20", "訊號", "操作建議", "投資人"])
    if has_news and not has_invest:
        # 新聞豐富但完全沒投資連結 -> 可能是「純新聞稿」
        # 不直接扣分，但在 issues 裡標記
        warnings.append("[維度4-新聞遊離] 有新聞敘述但缺少明確投資啟示")
    elif not has_news and has_invest:
        score -= 0.5
        warnings.append("[維度4-新聞不足] 基本沒有AI/半導體動態，只有投資建議")

    # ── 維度5：André Kostolany 金句
    if "Kostolany" not in script and "科斯托蘭尼" not in script and "安德烈" not in script:
        score -= 1.0
        issues.append("[維度5-金句缺失] 沒有 André Kostolany 金句收尾")

    # ── 維度6：段落口語化 + 無系統痕跡
    system_markers = re.findall(r'\(系統[^\)]+\)|\(本腳本[^\)]+\)|\(AI[^\)]+\)', script)
    if system_markers:
        score -= 2.0
        issues.append(f"[維度6-系統痕跡] {system_markers}")

    # ── 維度7：過渡句
    filler_phrases = re.findall(r'以下是|根據我們的|讓我們看看|根據我們的資料', script)
    if filler_phrases:
        score -= 0.5
        warnings.append(f"[維度7-過渡句] 發現: {set(filler_phrases)}")

    # ── 維度8：股票代碼洩漏（非 TWII/QQQ/SPY 之類）
    leaked_codes = re.findall(r'\^[A-Z]{2,5}:|\b[A-Z]{2,5}\.TW\b|\b[A-Z]{4,5}\b(?=:|：)', script)
    # 過濾合理的股票名稱提及（輝達、谷歌等）
    name_leaked = [c for c in leaked_codes if c not in ["輝達", "谷歌", "Meta", "微軟", "蘋果", "特斯拉"]]
    if name_leaked:
        score -= 1.5
        warnings.append(f"[維度8-代碼洩漏] {set(name_leaked[:3])}")

    final_score = max(0.0, score)
    passed = final_score >= 7.0 and len([i for i in issues if not i.startswith("[維度7")]) == 0

    diag = {
        "pass": passed,
        "score": round(final_score, 2),
        "issues": issues,       # 需要馬上處理的問題
        "warnings": warnings,  # 緩慢改進的問題
        "pos_sig": pos_sig,
        "has_ai_hook": has_ai_hook,
    }
    _lfl(mode, "|".join([i for i in issues]), script[:100])
    return diag

def _analyze_fail_patterns(mode, limit=10):
    """從失敗日誌中萃取根因模式（供主動式改進用）"""
    if not _FB_LOG.exists():
        return []
    try:
        fb = json.loads(open(_FB_LOG).read())
        recent = [f for f in fb[-limit:] if f.get("mode") == mode]
        # 統計失敗原因頻率
        patterns = {}
        for f in recent:
            reason = f.get("reason", "")
            # 解析 reason 格式: "[維度X-標籤]內容" 或 plain string
            m = re.match(r'\[(維度\d[^\]]+)\]', reason)
            key = m.group(1) if m else (reason[:30] if reason else "unknown")
            patterns[key] = patterns.get(key, 0) + 1
        # 回傳按頻率排序的 Top-3 失敗模式
        sorted_pat = sorted(patterns.items(), key=lambda x: -x[1])
        return [f"{k}（{v}次）" for k, v in sorted_pat[:3]]
    except Exception:
        return []

def post_gen_eval(mode, script):
    cfg = _lcfg()
    q = validate_quality(script, mode)
    qs = q.get("score", 7.0)
    scs = []
    if _SCORES.exists():
        scs = json.loads(open(_SCORES).read())

    entry = {
        "date": datetime.date.today().isoformat(),
        "mode": mode,
        "score": qs,
        "passed": q.get("pass", True),
        "issues": q.get("issues", []),
        "warnings": q.get("warnings", []),
    }
    scs.append(entry)
    open(_SCORES, "w", encoding="utf-8").write(json.dumps(scs[-50:], ensure_ascii=False, indent=2))
    logger.info(f"  腳本質檢 score={qs:.1f} | 問題={q.get('issues',[])} | 警示={q.get('warnings',[])}")

    target = cfg.get("target", 8.0)
    # 觸發閾值更敏感：任何 issues 或連續 2 次 warnings 都考慮改進
    has_critical = bool(q.get("issues"))
    has_warnings = bool(q.get("warnings"))

    if (qs < target - 1.5 and len(scs) >= 2) or (has_critical and len(scs) >= 1):
        logger.info(f"  觸發主動式Prompt優化 score={qs} 問題數={len(q.get('issues',[]))}+{len(q.get('warnings',[]))}")
        _do_proactive_iter(mode, script, q, cfg)
    elif has_warnings and len(scs) >= 3:
        # 連續預警：主動蒸餾正樣本特徵
        logger.info(f"  觸發正樣本特徵蒸餾（warnings累積）")
        _distill_positive_features(mode, cfg)
    return q

def _distill_positive_features(mode, cfg):
    """從歷史高分 Prompt 版本中蒸餾正向特徵，不用大改只是小修"""
    if not cfg.get("ena", True):
        return
    if not _SCORES.exists():
        return

    try:
        scs = json.loads(open(_SCORES).read())
        recent = [s for s in scs[-10:] if s.get("mode") == mode and s.get("passed") and s.get("score", 0) >= 8.0]
        if len(recent) < 3:
            return  # 不夠正樣本，跳過

        sc_ver = _lcfg()
        best_ver_path = PROMPT_DIR / f"v{sc_ver.get('bv', 1)}.json"
        if not best_ver_path.exists():
            return

        with open(best_ver_path, encoding="utf-8") as f:
            best_data = json.load(f)

        # 從 best version 的 prompt 抽出結構特徵
        best_prompt = best_data.get("stw" if mode == "tw" else "sus", "")

        # 萃取段落結構關鍵詞
        prompt = f"""你是 Prompt 蒸餾專家。從以下高質量 Prompt 片段中，萃取 2-3 個「讓 Podcast 腳本質感升級」的寫作特徵，用於微調 System Prompt。

【高質量 Prompt（精華部分）】:
{best_prompt[:1500]}

【蒸餾要求】:
1. 找出該 Prompt 中「對寫作風格有正面影響」的描述（例如：鉤子句式、段落銜接、用詞引導）
2. 不要抄襲原文，而是萃取「原則+範例」的組合模式
3. 只輸出 JSON：{{"features":["特徵1：具體描述","特徵2：具體描述","特徵3：具體描述"]}}"""
        r = call_nim(prompt, task_type="medium", temperature=0.6, max_tokens=1500)
        if r:
            m = re.search(r'"features"\s*:\s*\[([^\]]+)\]', r, re.DOTALL)
            if m:
                logger.info(f"  正樣本特徵蒸餾結果: {m.group(0)[:150]}")
    except Exception as e:
        logger.warning(f"Feature distillation failed: {e}")

def _do_proactive_iter(mode, script, diag, cfg):
    """
    主動式 Prompt 改進（非被動追加禁止規則）：
      Step 1: 多維診斷（哪些維度失敗 + 為什麼失敗）
      Step 2: 分析失敗根因（歷史模式）
      Step 3: 對比正樣本（有 quality ≥ 8.5 的歷史版本嗎？）
      Step 4: 生成改進後 Prompt（含正向引導 + 負向規則）
    """
    if not cfg.get("ena", True):
        return

    issues = diag.get("issues", [])
    warnings = diag.get("warnings", [])
    fail_patterns = _analyze_fail_patterns(mode)

    current_prompt = cfg.get("sys_tw" if mode == "tw" else "sys_us", "")

    # 嘗試找高分正樣本
    best_snippet = ""
    try:
        scs = json.loads(open(_SCORES).read()) if _SCORES.exists() else []
        high_score = [s for s in scs[-20:] if s.get("mode") == mode and s.get("score", 0) >= 8.5 and s.get("passed")]
        if high_score:
            # 找對應版本的 prompt snippet
            ver_data = {}
            if _SCORES.exists():
                sc_ver = _lcfg()
                bfn = PROMPT_DIR / f"v{sc_ver.get('bv', 1)}.json"
                if bfn.exists():
                    with open(bfn, encoding="utf-8") as f:
                        ver_data = json.load(f)
            best_snippet = ver_data.get("stw" if mode == "tw" else "sus", "")[:400]
    except Exception:
        best_snippet = ""

    # 診斷摘要（供 LLM 理解根因）
    diagnosis = []
    if issues:
        diagnosis.append(f"【關鍵問題】: {'; '.join(issues)}")
    if warnings:
        diagnosis.append(f"【需要注意】: {'; '.join(warnings)}")
    if fail_patterns:
        diagnosis.append(f"【歷史失敗模式】: {'; '.join(fail_patterns)}")
    diag_text = "\n".join(diagnosis) if diagnosis else "【新問題】腳本質量未達標準"

    OPT = f"""你是 Prompt Engineering 專家，負責「主動式質量提升」而非「被動追加禁止規則」。

## 任務
根據壞腳本質檢報告，系統性地改進 System Prompt，讓未來生成的腳本質量和風格全面提升。

## 壞腳本質檢報告
```
{diag_text}
```

## 壞腳本（完整）
```
{script}
```

## 當前 System Prompt（片段）
```
{current_prompt[:800]}
```

## 正樣本特徵（蒸餾自高分歷史版本，如有）
```
{best_snippet}
```

## 主動式改進要求（嚴格執行）
1. **根因修復**：不只是追加禁止規則，而是找出「什麼寫作模式導致問題」，在原則區段清楚說明正確做法
2. **正向示範**：在 System Prompt 中加入「✅ 正確示例」段落，示範如何寫好鉤子、如何說投資啟示、如何自然收尾
3. **比例引導**：再次強調「70% AI 新聞動態 + 30% 投資啟示」的結構，在【腳本內容比例指引】中說明
4. **不退步**：不得刪除或弱化現有任何核心原則，只能加強
5. **每次只做 1-2 個主要改動**：避免一次性大幅重寫，導致其他維度退化

## 輸出格式
只需輸出 JSON，格式如下：
{{
  "diagnosis": "失敗根因分析（1-2句）",
  "changes": ["具體改動1", "具體改動2"],
  "improved": "完整的新 System Prompt（全文，不可截斷）"
}}"""

    try:
        r = call_nim(OPT, task_type="medium", temperature=0.7, max_tokens=3500)
        if r:
            m = re.search(r'\{.*"improved"\s*:\s*"([^"]+(?:[^\\]"[^"]*)*)"\s*\}', r, re.DOTALL)
            # 也支持 improved 在前面的格式
            if not m:
                m = re.search(r'"improved"\s*:\s*"(.*?)"(?:,|\n|\s*\})', r, re.DOTALL)
            if m:
                imp = m.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\r', '')
                nv = cfg.get("v", 1) + 1
                k = "sys_tw" if mode == "tw" else "sys_us"
                old_prompt = cfg.get(k, "")
                cfg[k] = imp
                cfg["v"] = nv
                _scfg(cfg)
                _sver(nv, cfg.get("sys_tw", ""), cfg.get("sys_us", ""),
                      diag.get("score", 0), f"[主動改進]{diag.get('issues', [])[:2]}")
                logger.success(f"  ✅ Prompt v{nv} 已更新 | 改動: {r[:100]}")
                if diag.get("score", 0) > cfg.get("bs", 0):
                    cfg["bv"] = nv
                    cfg["bs"] = diag.get("score", 0)
                    _scfg(cfg)
                return

            # fallback: 嘗試解析變動描述
            diag_m = re.search(r'"diagnosis"\s*:\s*"([^"]+)"', r)
            if diag_m:
                logger.info(f"  Prompt改進診斷: {diag_m.group(1)}")
    except Exception as e:
        logger.warning(f"Proactive iteration failed: {e}")

# ── 前置處理器 ───────────────────────────────────────────────────
def _clean_html(text):
    if not text: return ""
    text=re.sub(r'<[^>]+>','',text)
    text=re.sub(r'\s+',' ',text).strip()
    return text

def _interpret_sentiment(score, bullish_ratio=None):
    if score is None: return "目前市場情緒混沌，方向不明"
    if score>=0.5: bias="偏多"
    elif score>=0.1: bias="輕微偏多"
    elif score>-0.1: bias="中性"
    elif score>-0.5: bias="輕微偏空"
    else: bias="偏空"
    if bullish_ratio is not None and bullish_ratio>=0.6: bias=f"{bias}，看漲新聞佔多數"
    elif bullish_ratio is not None and bullish_ratio<=0.3: bias=f"{bias}，看跌新聞佔多數"
    return bias

def _interpret_technical(trend, volatility, rsi=None, macd=None):
    t={"BULLISH":"多方格局","BEARISH":"空方格局"}.get(trend,"觀望格局")
    v="波動激烈" if volatility and volatility>3 else "波動適中" if volatility and volatility>1.5 else "波動平穩" if volatility else ""
    rsi_t=""
    if rsi:
        rsi_t="有過熱跡象" if rsi>70 else "處於超賣區，可能有反彈機會" if rsi<30 else "處於偏多區" if rsi>55 else "處於偏空區" if rsi<45 else ""
    parts=[p for p in[t,v,rsi_t] if p]
    return "，".join(parts)

def _summarize_market_us(market):
    """
    US 市場摘要：只聚焦科技股ETF（QQQ），大盤SPY只作語境。
    回傳 (summary_str, spike_info) 或 (None, None)。
    """
    if not market:
        return "美股今日數據暫時無法取得。", None

    spy=market.get("SPY"); qqq=market.get("QQQ")
    lines=[]; spike=None

    if spy and spy.get('close',0)!=0:
        chg=spy.get('change',0)
        if chg>1.5: lines.append(f"昨夜美股大盤大漲{abs(chg):.1f}%，市場情緒偏多。")
        elif chg<-1.5: lines.append(f"昨夜美股大盤重挫{abs(chg):.1f}%，市場氣氛緊張。")
        elif chg>0: lines.append("昨夜美股大盤上漲，整體氛圍偏多。")
        elif chg<0: lines.append("昨夜美股大盤下跌，市場情緒偏謹慎。")
        else: lines.append("昨夜美股大盤大致持平，觀望氣氛濃。")

    if qqq and qqq.get('close',0)!=0:
        chg=qqq.get('change',0)
        icon="▲" if chg>=0 else "▼"
        if chg>3: emphasis="大漲"; spike=("科技股ETF大漲",chg,"bullish",icon)
        elif chg>1: emphasis="上漲"
        elif chg<-3: emphasis="暴跌"; spike=("科技股ETF暴跌",chg,"bearish",icon)
        elif chg<-1: emphasis="回落"
        else: emphasis="小幅震盪"
        lines.append(f"科技股ETF{emphasis}，{icon}{abs(chg):.2f}%。")
    else:
        lines.append("科技股ETF暫無數據。")

    return " ".join(lines) if lines else "美股今日走勢平淡，指數在狹幅區間整理。", spike

def _summarize_market_tw(market):
    if not market:
        return "台股今日數據暫時無法取得。"
    lines=[]
    twii=market.get("^TWII")
    if twii and twii.get('close',0)!=0:
        chg=twii.get('change',0)
        icon="▲" if chg>=0 else "▼"
        vol=twii.get('volume',0)
        vol_text=f"成交金額{vol/1e8:.1f}億" if vol>0 else ""
        lines.append(f"台灣加權指數{'上漲' if chg>=0 else '下跌'}，{icon}{abs(chg):.2f}%，{vol_text}。")
    for sym in ["0050.TW","2330.TW"]:
        info=market.get(sym)
        if not info or info.get('close',0)==0: continue
        chg=info.get('change',0)
        lines.append(f"{_n(sym)}{'上漲' if chg>=0 else '下跌'} {abs(chg):.2f}%。")
    return " ".join(lines) if lines else "台股今日數據暫時無法取得。"

def _summarize_market_analysis(market_analysis, mode):
    if not market_analysis: return ""
    focus={"QQQ"} if mode=="us" else {"^TWII","0050.TW","2330.TW"}
    lines=[]
    for sym,result in market_analysis.items():
        if sym not in focus or not isinstance(result,dict): continue
        name=_n(sym); trend=result.get('trend','NEUTRAL')
        vol=result.get('volatility',0); inds=result.get('technical_indicators',{})
        rsi=inds.get('rsi'); macd=inds.get('macd')
        tech_desc=_interpret_technical(trend,vol,rsi,macd)
        report=result.get('report','')
        report_clean=re.sub(r'RSI\s*[\d.]+','',str(report))
        report_clean=re.sub(r'MACD\s*[-\d.]+','',report_clean).strip()
        if report_clean and "無" not in report_clean[:4] and len(report_clean)>10:
            lines.append(f"{name}：{tech_desc}，{report_clean}")
        else:
            lines.append(f"{name}：{tech_desc}。")
    return " ".join(lines) if lines else ""

def _filter_news(news, mode):
    """
    新聞過濾：聚焦 AI Agent 產品/生態/投資動態，為 70% 內容比例服務。
    優先順序：
      1. AI Agent / Agent Framework 產品發布
      2. 大模型更新、性能報告、商用部署
      3. 重要融資/併購/政策監管
      4. 半導體先進製程/AI 晶片（供應鏈視角）
    """
    if not news: return []

    # AI Agent 核心關鍵詞（第一優先，含 AI Agent/Agent 產品）
    core_agent_kw = [
        'AI Agent', 'Agent', 'OpenAI', 'Anthropic', 'ChatGPT', 'Claude',
        'Gemini', 'Grok', 'Llama', 'xAI', 'Perplexity', 'Cursor',
        'AutoGPT', 'Auto agent', 'MCP', 'model context protocol',
        'ReAct', 'RAG', 'AI assistant', 'AI assistant', 'Copilot',
        '機器人', 'robot', 'Figure', '1X', 'Boston Dynamics', 'Tesla Bot',
        'humanoid robot', 'AI model', 'foundation model',
    ]
    # 大模型 / 半導體次優先
    secondary_kw = [
        '半導體', '晶片', 'AI', '人工智慧', '機器學習', '輝達', 'NVIDIA',
        '台積電', 'TSMC', 'nvidia', '先進製程', '2奈米', '3奈米', '5奈米',
        '7奈米', 'HBM', '記憶體', 'ASIC', 'FPGA', 'SoC',
        'data center', 'AI server', 'edge AI', 'CoWoS', '先進封裝',
        'ASIC', 'AI 晶片', 'GPU server',
    ]
    ex_tw = ['巴西', 'Jio', 'BYD匈牙利', '印度IPO', '比特幣', '星鏈', '餐廳', '披薩', 'IPO',
             '比特幣', '比特幣', '足球', '籃球', 'MLB', 'NBA', '網球']
    ex_us = ['美國大選', '總統大選', '足球', '網球', 'NBA', 'MLB', '電影', 'Netflix',
             'Fed', '美聯準', '利率', '降息', '升息']

    scored = []
    for item in news[:15]:  # 擴大範圍以便篩選
        title = _clean_html(item.get('title', ''))
        desc  = _clean_html(item.get('description', ''))
        combined = title + " " + desc
        if len(title) < 8:
            continue

        # 排除
        ex = ex_tw if mode == 'tw' else ex_us
        if any(e in combined for e in ex):
            continue

        # 評分
        score = 0
        matched_kw = []
        for kw in core_agent_kw:
            if kw.lower() in combined.lower():
                score += 3
                matched_kw.append(kw)
        for kw in secondary_kw:
            if kw.lower() in combined.lower():
                score += 1
                matched_kw.append(kw)

        if score == 0:
            continue

        if len(desc) > 200:
            desc = desc[:200] + "..."

        scored.append({"score": score, "title": title, "desc": desc,
                       "kw": matched_kw[:3]})

    # 按分數排序，取最高分的 news（按 70% 比例邏輯：優先 Agent 新聞）
    scored.sort(key=lambda x: -x["score"])
    result = []
    for item in scored[:4]:
        result.append(f"{item['title']}。{item['desc']}")

    return result  # 直接返回完整句，不必再加前綴

def _summarize_strategies(strategy_results, mode):
    if not strategy_results: return "今日策略分析暫無結果。"
    lines=[]
    focus={"QQQ"} if mode=="us" else {"0050.TW","^TWII","2330.TW"}
    for sym,result in strategy_results.items():
        if sym not in focus or not isinstance(result,dict): continue
        name=_n(sym)
        # 只取 god_system（MA20），不管其他策略
        gs=result.get('strategies',{}).get('god_system')
        if gs:
            position=gs.get('signals',{}).get('position','NEUTRAL')
            expected_ret=gs.get('expected_return',0)
        else:
            position=result.get('signals',{}).get('position','NEUTRAL')
            expected_ret=result.get('expected_return',0)

        if position=='LONG': pos_text="多方"; action="建議分批布局"
        elif position=='SHORT': pos_text="空方"; action="建議減碼或觀望"
        else: pos_text="中性觀望"; action="建議區間操作或不進場"

        ret_text=f"，MA20模型預期波動回報{expected_ret:.2f}%" if expected_ret!=0 else ""
        lines.append(f"{name}訊號「{pos_text}」，{action}{ret_text}。")
    return " ".join(lines) if lines else "今日 MA20 均線策略訊號均為觀望，指數可能處於整理格局。"

# ── Prompt 建構 ───────────────────────────────────────────────────
def _build_user_prompt(mode, today, analysis, news_str, sentiment_desc,
                       market_analysis_str, strategy_str, spike_info=None, filtered_news=None):
    mode_upper=mode.upper()

    # Hook
    hook_line=""
    if spike_info:
        lbl,chg,direction,_=spike_info
        lbl_s=lbl.replace("科技股ETF大漲","{{科技股ETF}}大漲").replace("科技股ETF暴跌","{{科技股ETF}}暴跌")
        lbl_s=lbl_s.replace("台積電大漲","{{台積電}}大漲").replace("台積電大跌","{{台積電}}大跌")
        if direction=="bullish":
            hook_line=(f"【今日重點】{lbl}了 {abs(chg):.1f}%。"
                       "請在開頭第1句話用「今天值得留意，"
                       f"{lbl_s}了⋯背後透露什麼訊號？」吸引聽眾興趣。")
        else:
            hook_line=(f"【市場警訊】{lbl}了 {abs(chg):.1f}%。"
                       "請在開頭第1句話用「市場出現警訊，"
                       f"{lbl_s}了⋯這代表什麼？」引起注意。")
    elif mode=='us':
        hook_line="【開場提示】昨晚美股牽動全球資金神經。請在第1句就告訴聽眾最重要的一件事。"
    else:
        hook_line="【開場提示】台股今天有哪些值得關注的信號？請在第1句就說明市場最大亮點。"

    # 24h News
    news_24h=""
    if filtered_news:
        titles=[]
        for item in filtered_news[:3]:
            # 兼容：_filter_news 現在返回字串；_generate_fallback_natural 可能傳入 dict
            if isinstance(item, dict):
                title_raw = item.get('title', str(item))
            else:
                title_raw = str(item)
            t = title_raw.split("。")[0]
            if "：" in t: t=t.split("：")[1]
            if len(t)>4: titles.append(t.strip())
        if titles:
            news_24h="；".join([f"{['第一個','第二個','第三個'][i]}，{t}" for i,t in enumerate(titles[:3])])

    return f"""請生成一段 {mode_upper} 投資大師 Podcast 逐字稿。

【黃金內容比例：70/30】
- 70% 篇幅：AI Agent 最新動態（2-4則新聞，每則展開成120-180字的完整段落，含事件+對投資人的意義）
- 30% 篇幅：對應的投資啟示（MA20策略訊號、方向建議、倉位提示）
- 兩者必須邏輯連結：看完美聞要知道「這對我的持倉意味著什麼」

【硬性字數要求】
本腳本必須至少產生2500個中文字符（約7分鐘普通話語音的量）。
每一段都要寫完整、寫充實——不要只寫一句話就跳到下一段，必須有完整的「事件描述」→「對投資人的啟示」敘述。
如果輸出的總字數少於2500字，請繼續擴展每一段直到達標為止。

【結構要求：自然段落，不要分段】
全程使用流暢的普通話，口語化表達，直接可由 TTS 語音朗讀。
不要用任何分隔符（'-'、'*'、'【】'、'｜'），不要有任何橋段標題（「市場概況：」「策略分析：」之類）。
開頭第一句即為「歡迎收聽《幫幫忙說AI投資》，我是幫幫忙。今天是{today}。」

【鉤子設計（開場第1句最重要）】
  暴漲/暴跌情形：「今天值得留意，{{科技股ETF}}/{{台積電}}突然大漲了X%⋯背後透露什麼訊號？」
  AI 重大新聞情境：「今天AI圈有一個重要消息，可能影響你未來三個月的投資方向⋯」（優先使用）
  普通情形：「昨晚美股/台股開盤後，出現了一個值得關注的信號⋯」

【股名轉換（強制）】
  TWII → 加權指數；2330 → 台積電；0050 → 元大台灣50
  QQQ  → 科技股ETF；SPY → 美股大盤

【今日 AI Agent / 半導體 動態（70% 核心區塊）】
以下新聞已幫您過濾為半導體與 AI 相關，請將每則新聞展開成 120-180 字的完整段落，
涵蓋「發生了什麼關鍵事件」與「對投資大眾的意義或影響」的完整敘述：
{news_str}

【市場總基調 + 技術參考（30% 區塊起點）】
{sentiment_desc}
{market_analysis_str or '技術面無特殊發現。'}
{analysis}

【MA20 均線策略結論（30% 區塊核心）】
{strategy_str}

【完整段落流程（請自然流暢執行，不要分段標記）】
第1段（開場50字）：「歡迎收聽⋯我是幫幫忙。今天是{today}。」
  + 一句話說今天最重要的一件事（鉤子或 AI 重大新聞預告）

第2-5段（AI 新聞，70% 區塊）：
  - 每則新聞獨立成段（120-180字），結構：「事件描述」→「對你的投資意味着什麼」
  - US版：聚焦 OpenAI / Anthropic / Google / Meta / xAI / 機器人 / Agent 部署
  - TW版：聚焦台積電、先進封裝、先進製程、IC設計、AI伺服器供應鏈

第6-7段（投資啟示，30% 區塊）：
  - 先用 1-2 句話說技術面/情緒面 →馬上接「對操作來說⋯」
  - 明確說出「多方布局」或「空方減碼」或「觀望不進場」（立場鮮明，立場鮮明，立場鮮明）
  - 最多提到 {mode=='us' and '科技股ETF' or '元大台灣50／加權指數'}，不加其他個股

第8段（金句收尾40字以內）：André Kostolany 金句，與當日情緒呼應，自然收尾

【禁止行為（LLM 必須遵守）】
- 絕對不要朗讀股票代碼
- 絕對不要朗讀技術指標數值（RSI、MACD、Bollinger 的數字全部不朗讀）
- 絕對不要朗讀情緒分數
- 絕對不要羅列所有股票（最多2檔，除非有超過±3%的劇烈波動）
- US版：不要提及加權指數、元大台灣50
- TW版：不要提及纳兹达克（只能作背景引用）
- 不要有任何「以下是...」「根據我們的...」「讓我們看看...」這類過渡句
- 絕對不要包含「(系統備註)」「(本腳本由AI生成)」
- 不要分段，用純散文敘述
- 絕對不要只報新聞、不說投資啟示（每段AI新聞後至少暗示「對投資人的意義」）
"""

# ── LLM 生成 ─────────────────────────────────────────────────────
MIN_CHARS = 2500  # 7分鐘普通話約需2500字，這是最低門檻

def _expand_section(section_type, current_text, system_prompt, max_tokens=4000):
    """
    多段擴展：用獨立的 prompt 請求模型繼續扩充某個段落。
    section_type: "news" | "strategy" | "all"
    """
    expand_prompts = {
        "news": (
            "你是一個專業的Podcast主持人助理。你的任務是將下面的AI新聞段落徹底擴展，使其更詳細、更有深度。"
            "每則新聞必須擴展為150-200字的完整段落，包含以下全部內容：\n"
            "【A】事件的背景與具體細節（誰、什麼時候、在哪裡、為什麼重要）\n"
            "【B】對普通投資人的具體意義（這會怎麼影響他們的科技股ETF倉位？）\n"
            "【C】短期與長期的市場影響（未來3-12個月的預期）\n\n"
            "現有內容：\n{content}\n\n"
            "【嚴格要求】擴展時不要截斷或省略任何現有內容，要完整保留並大幅延伸每個段落。"
            "每則新聞擴展後的段落必須達到150-200字，全文至少{target}字。"
        ),
        "strategy": (
            "你是一個專業的Podcast主持人助理。請將下面的投資策略段落大幅擴展，使其更有說服力和可操作性。"
            "必須包含：\n"
            "【一】當前宏觀市場情緒與技術面的具體描述\n"
            "【二】MA20均線策略訊號的明確解讀\n"
            "【三】對三種不同投資人的具體操作建議：已經持有科技股ETF的人、觀望中的人、風險偏好極低的人\n"
            "【四】風險提示與紀律建議\n\n"
            "現有內容：\n{content}\n\n"
            "【嚴格要求】保留並擴展所有現有內容，每個要點展開成至少80字。"
            "策略段落總字数至少達到400字。"
        ),
        "all": (
            "你是一個專業的Podcast主持人助理。下面的腳本內容不足，你需要徹底擴展每個段落。"
            "操作方法：對腳本中的每個AI新聞段落，擴展到150-200字，包含背景、細節、投資意涵。"
            "對投資策略段落，展開為含具體操作建議的完整段落。"
            "對開場段落，加入更多具體的市場情緒描述。"
            "對金句段落，與當日情緒完整呼應。\n\n"
            "現有內容：\n{content}\n\n"
            "【嚴格要求】完整保留並擴展原文，不要刪除任何內容，只是讓每個段落更長、更詳細。"
            "擴展後全文必須至少{target}個中文字符。"
        ),
    }
    tmpl = expand_prompts.get(section_type, expand_prompts["all"])
    # 計算目標
    need = max(0, (MIN_CHARS if section_type == "all" else MIN_CHARS // 4) - len(current_text))
    if need < 200 and section_type == "all":
        return current_text  # 差距太小不折騰

    prompt = tmpl.format(content=current_text, target=MIN_CHARS)
    logger.info(f"  🔄 多段擴展 ({section_type}), 差距={need}字, 呼叫 NIM...")
    # 擴展用 deepseek-v3.2（有思考模式，比 llama 更能生成長文本）
    # fallback 到 llama-3.3-70b（萬一 deepseek 失敗）
    result = call_nim(prompt=prompt, task_type="script", temperature=0.6,
                      max_tokens=max_tokens, system=system_prompt)
    if result and len(result) > len(current_text):
        return result
    return current_text  # 擴展失敗，回退

def _build_multi_pass_plan(filtered_news, mode):
    """
    根據新聞數量規劃每段的目標字數，確保總字數達到 MIN_CHARS。
    """
    n_news = len(filtered_news) if filtered_news else 2
    # 每則新聞目標150字,開場100字,策略200字,金句50字
    estimated = 100 + n_news * 150 + 200 + 50
    return estimated

def _generate_long_script(user_prompt, system_prompt=None):
    """
    多段生成策略（v2）：
    1. 先完整生成一次（llama-3.3-70b）
    2. 如果 < MIN_CHARS，執行 all→news→strategy→all 共4次擴展
    3. 每輪擴展後記錄長度，達標則提前終止
    """
    # ── 第一輪：初始生成 ──────────────────────
    logger.info("開始使用 NIM API 生成文字稿（長度優化模式）...")
    result = call_nim(prompt=user_prompt, task_type="script", temperature=0.7,
                      max_tokens=8000, system=system_prompt)
    if not result:
        logger.error("NIM API 失敗")
        return None

    logger.success("✓ NIM API 成功生成文字稿")
    chars = len(result)
    logger.info(f"  第1輪輸出：{chars} 字（目標：≥{MIN_CHARS}字）")

    # ── 第二輪起：多段擴展（固定4次，確保長度達標） ───────────────
    if chars < MIN_CHARS:
        logger.info(f"  ⚠  長度不足，觸發多段擴展...")

        # 擴展順序：all → news → strategy → all（每輪都執行，除非已超標）
        for pass_idx, stype in enumerate(["all", "news", "strategy", "all"], start=2):
            if chars >= MIN_CHARS:
                logger.info(f"  ✅ 已達標（{chars}字），跳過剩餘擴展")
                break

            prev_chars = chars
            tokens = 8000  # 都用最大 tokens 鼓勵長輸出
            result = _expand_section(stype, result, system_prompt, max_tokens=tokens)
            chars = len(result) if result else prev_chars
            delta = chars - prev_chars
            if delta > 0:
                logger.info(f"  第{pass_idx}輪 [{stype}] → {chars} 字 (+{delta})")
            else:
                logger.warning(f"  第{pass_idx}輪 [{stype}] 無改善，仍為 {chars} 字")

    return result

def generate_script_with_llm(prompt, system_prompt=None):
    return _generate_long_script(prompt, system_prompt=system_prompt)

# ── 主生成流程 ───────────────────────────────────────────────────
def generate_script(market_data, mode, strategy_results, market_analysis):
    today=datetime.date.today().strftime('%Y年%m月%d日')
    market=market_data.get('market',{})

    spike_info=None
    if mode=='us':
        analysis,spike_info=_summarize_market_us(market)
    else:
        analysis=_summarize_market_tw(market)
        tw_m=market.get("2330.TW",{})
        if tw_m.get("change",0)>2:
            spike_info=("台積電大漲",tw_m.get("change",0),"bullish","▲")
        elif tw_m.get("change",0)<-2:
            spike_info=("台積電大跌",tw_m.get("change",0),"bearish","▼")

    filtered_news=_filter_news(market_data.get('news',[]),mode)
    news_str="\n".join(filtered_news) if filtered_news else "今日無重要半導體或AI相關產業新聞。"

    sentiment=market_data.get('sentiment',{})
    sentiment_desc=_interpret_sentiment(sentiment.get('overall_score'),sentiment.get('bullish_ratio'))

    market_analysis_str=_summarize_market_analysis(market_analysis,mode)
    strategy_str=_summarize_strategies(strategy_results,mode)

    system_prompt=_get_sys(mode)
    user_prompt=_build_user_prompt(mode,today,analysis,news_str,sentiment_desc,
                                   market_analysis_str,strategy_str,
                                   spike_info=spike_info,filtered_news=filtered_news)

    script=generate_script_with_llm(user_prompt,system_prompt=system_prompt)

    if script:
        # 清理殘留系統文字
        lines=script.splitlines(); clean=[]
        for line in lines:
            line=re.sub(r'\(系統備註[^\)]*\)','',line)
            line=re.sub(r'\【系統備注[^\】]*】','',line)
            line=re.sub(r'\(本脚[^\)]*\)','',line)
            line=re.sub(r'\(AI[^\)]*\)','',line)
            line=re.sub(r'\(LLM[^\)]*\)','',line)
            line=line.strip()
            if line and len(line)>2: clean.append(line)
        script="\n".join(clean)
        post_gen_eval(mode,script)
        return script

    logger.warning("所有 LLM API 不可用，使用自然敘事 Fallback")
    return _generate_fallback_natural(today,analysis,news_str,sentiment_desc,
                                       strategy_str,mode,spike_info=spike_info,
                                       filtered_news=filtered_news)

# ── Fallback（LLM 完全不可用時） ─────────────────────────────────
def _generate_fallback_natural(today,analysis,news_str,sentiment_desc,
                                strategy_str,mode,spike_info=None,filtered_news=None):
    """
    Fallback 腳本：同樣遵守 70/30 黃金比例。
    如果有 filtered_news，以 AI 新聞為主（70%），投資啟示為輔（30%）。
    """
    tmap={"偏多":"市場呈現多頭格局","大幅偏多":"市場人氣高漲，資金行情明顯",
          "輕微偏多":"市場略有回暖跡象","偏空":"承壓方向偏空","大幅偏空":"市場恐慌情緒蔓延",
          "中性":"來到關鍵十字路口","輕微偏空":"方向略偏謹慎"}
    st=next((tmap[k] for k in tmap if k in sentiment_desc),"方向待確認")

    # 開場鉤子
    if spike_info:
        lbl,chg,dir,_=spike_info
        hook=(f"今天值得留意：{lbl}了{abs(chg):.1f}%。"
              f"背後透露什麼訊號？{st}，一起來看。") if dir=="bullish" else (
              f"市場出現警訊：{lbl}了{abs(chg):.1f}%。這代表什麼？{st}，一起來看。")
    elif filtered_news and any(kw in str(filtered_news) for kw in ['Agent', 'AI', 'OpenAI', 'Anthropic', 'Gemini', 'Grok']):
        hook="今天AI圈有一個重要消息，可能影響你未來三個月的投資方向，一起來看。"
    elif mode=='us':
        hook=f"昨晚美股牽動全球資金神經。{st}，今天哪些變化值得我們關注？一起來看。"
    else:
        hook=f"台股今天吸引了市場目光。{st}，哪些信號值得我們留意？一起來看。"

    # AI 新聞區塊（70%）- _filter_news 現在已返回完整句
    news_block = ""
    if filtered_news:
        items = filtered_news[:4]  # 最多4則
        segs = []
        labels = ["第一個動態", "第二個動態", "第三個動態", "第四個動態"] if len(items) <= 4 else ["首個", "第二", "第三"]
        for i, item in enumerate(items):
            title = item.get('title', item) if isinstance(item, dict) else item
            # 如果直接是字符串，取第一句當標題
            if isinstance(title, str) and "。" in title:
                title = title.split("。")[0]
            if len(title) > 5:
                segs.append(f"{labels[i]}，{title}。這個消息對投資人有什麼啟示？值得我們持續關注。")
        if segs:
            news_block = "。".join(segs) + "。"
    else:
        news_block = f"今日 AI 與半導體供應鏈方面，{news_str}"

    # 操作建議（30%，立場鮮明）
    if "多方" in strategy_str or "布局" in strategy_str:
        sig="操作層面，MA20均線顯示多方訊號，建議分批布局、控制倉位。"
    elif "空方" in strategy_str or "減碼" in strategy_str:
        sig="操作層面，MA20均線呈空方訊號，建議觀望或減碼控制風險。"
    else:
        sig="操作層面，MA20均線顯示震盪整理，建議區間操作或不進場。"

    return (
        f"歡迎收聽《幫幫忙說AI投資》，我是幫幫忙。今天是{today}。\n\n"
        f"{hook}\n\n"
        f"{news_block}\n\n"
        f"情緒面{st}，{sentiment_desc}。\n\n"
        # 30% 區塊：市場背景 + 投資啟示
        f"{analysis}\n\n"
        f"{sig}\n\n"
        f"市場總是充滿著不確定性，但有紀律的投資人能從波動中發現機會。── André Kostolany\n\n"
        f"感謝各位的陪伴，我是幫幫忙，我們下次再見。"
    )
