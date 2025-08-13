下面给你一套**可直接落地**的設計與程式腳手架，使用 **CrewAI** 打造「0050 認知交易團隊 (Cognitive Trading Crew)」：以**週期性自我學習** + **日內全自動模擬交易**為核心；資料源以 `yfinance`（或可切換 TEJ API），回測用 `backtrader/vectorbt`，執行用自建紙上交易模組。你可以把整個專案當成一個 Python 套件或 Docker 服務部署。

---

# 架構總覽

**週期循環（每週末）**

1. 市場分析師 → 拉資料 + 指標特徵 → 週報
2. 策略開發師 → 讀週報 → 產生/改良策略（Python 策略碼）
3. 回測工程師 → 3 年歷史、留出最近 6 個月（防洩漏）→ 報告
4. 風控與模擬交易員 → 制度性門檻判斷（Sharpe>1、MDD<20% 等）→ 若通過，標記為**本週上線策略**

**日常（每個交易日）**
5\) 模擬交易員 → 依「本週策略」用即時/當日資料出信號 → 紙上交易 → 記錄與風控

---

# 目錄與設定

```
0050-ctc/
├─ config/
│  ├─ crew.yaml                 # agent 定義、工具、任務鏈
│  ├─ data.yaml                 # 資料源 / 交易成本 / 交易時區等
│  └─ risk.yaml                 # 風控與部署門檻
├─ data/                        # 快取資料與回測切片
├─ logs/                        # 任務、交易、回測日誌
├─ reports/                     # 週報、策略碼、回測報告、OOS表現
├─ strategies_library/          # 模板策略（均線、RSI、布林、突破…）
├─ crew/
│  ├─ agents.py
│  ├─ tasks.py
│  ├─ tools.py
│  └─ run_weekly.py             # 週期學習入口
├─ sim/
│  ├─ paper_broker.py           # 紙上交易帳戶
│  ├─ live_runner.py            # 每日模擬執行
│  └─ scheduler.py              # APScheduler / cron
├─ backtest/
│  ├─ bt_runner.py              # backtrader 執行器
│  └─ metrics.py
├─ prompts/
│  ├─ strategy_dev.md           # 策略生成提示模板（LLM）
│  └─ critique.md               # 風控回饋模板
├─ Dockerfile
└─ requirements.txt
```

---

# 關鍵設定（YAML 範例）

**config/data.yaml**

```yaml
symbol: "0050.TW"
timezone: "Asia/Taipei"
history_years: 3
oos_holdout_months: 6
source: "yfinance"   # or "tejapi"
fees:
  commission_rate_bps: 2   # 單邊 0.02%
  slippage_bps: 5          # 0.05% 模型滑點
bar: "1d"
```

**config/risk.yaml**

```yaml
deploy_thresholds:
  min_sharpe: 1.0
  max_mdd: 0.20
  min_trades: 30
  max_turnover_pa: 4.0   # 年換手率上限，控過度交易
positioning:
  max_gross_exposure: 1.0
  stop_loss_pct: 0.08
  take_profit_pct: 0.15
risk_checks:
  - "no_lookahead"
  - "train_test_split_respected"
  - "parameter_simplicity"
```

**config/crew\.yaml（CrewAI）**

```yaml
agents:
  market_analyst:
    role: "市場數據專家"
    goal: "統一拉取與清洗 0050 資料，抽取特徵並輸出週報"
    backstory: "精通時間序列與指標工程"
    tools: ["price_fetcher", "news_scraper"]
  strategy_dev:
    role: "量化策略設計師"
    goal: "根據週報產生具體策略代碼（backtrader 模式）"
    tools: ["strategy_templates", "python_sanity_checker"]
  backtest_engineer:
    role: "績效驗證官"
    goal: "嚴格回測，出具可重現的績效報告與圖表"
    tools: ["backtester", "metrics_calc", "plotter"]
  risk_sim:
    role: "執行與風控官"
    goal: "審核與部署至紙上交易；每日執行並監控風險"
    tools: ["paper_broker", "logger"]

tasks:
  - id: weekly_insight
    agent: market_analyst
    output: "reports/weekly_insight.json"
  - id: propose_strategy
    agent: strategy_dev
    input: "reports/weekly_insight.json"
    output: "reports/strategy_candidate.py"
  - id: backtest_strat
    agent: backtest_engineer
    input: "reports/strategy_candidate.py"
    output: "reports/backtest_report.json"
  - id: deploy_decision
    agent: risk_sim
    inputs:
      - "reports/backtest_report.json"
      - "reports/strategy_candidate.py"
    output: "reports/deployment_decision.json"
```

---

# 工具層（Tools）實作要點

**crew/tools.py（摘錄）**

```python
import json, os, pandas as pd, numpy as np, datetime as dt, yfinance as yf
from bs4 import BeautifulSoup
import requests

TAI_TZ = "Asia/Taipei"

def fetch_ohlcv(symbol: str, years: int = 3, bar="1d"):
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(days=365*years + 60)
    df = yf.download(symbol, start=start.date(), interval=bar, auto_adjust=True, progress=False)
    df = df.dropna().rename(columns=str.lower)  # ['open','high','low','close','adj close','volume']
    df.index = df.index.tz_localize("UTC").tz_convert(TAI_TZ)
    return df[['open','high','low','close','volume']]

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out['ret'] = out['close'].pct_change()
    out['ma20'] = out['close'].rolling(20).mean()
    out['ma60'] = out['close'].rolling(60).mean()
    out['rsi14'] = rsi(out['close'], 14)
    out['bb_mid'] = out['close'].rolling(20).mean()
    out['bb_std'] = out['close'].rolling(20).std()
    out['bb_up']  = out['bb_mid'] + 2*out['bb_std']
    out['bb_dn']  = out['bb_mid'] - 2*out['bb_std']
    out['atr14']  = atr(out, 14)
    return out.dropna()

def rsi(series, n=14):
    delta = series.diff()
    up = delta.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = -delta.clip(upper=0).ewm(alpha=1/n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - (100/(1+rs))

def atr(df, n=14):
    tr = np.maximum(df['high']-df['low'],
         np.maximum((df['high']-df['close'].shift()).abs(),
                    (df['low']-df['close'].shift()).abs()))
    return tr.rolling(n).mean()

def news_titles(keywords=["台灣50","台股權值股","景氣燈號"], limit=20):
    # 可換 Google News API；此處簡易示意（請遵守對應網站robots）
    results = []
    for kw in keywords:
        url = f"https://news.google.com/search?q={kw}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("a.DY5T1d")[:limit]:
            results.append({"kw": kw, "title": a.text.strip()})
    return results

def weekly_insight(symbol, years):
    df = add_indicators(fetch_ohlcv(symbol, years))
    vol = df['ret'].rolling(20).std().iloc[-1]
    trend = float((df['ma20'].iloc[-1] - df['ma60'].iloc[-1]) / df['ma60'].iloc[-1])
    regime = "trend" if trend>0 and vol<df['ret'].rolling(60).std().iloc[-1] else "range"
    report = {
        "asof": str(df.index[-1]),
        "stats": {
            "vol20": float(vol),
            "trend_ma20_ma60": trend,
            "atr14": float(df['atr14'].iloc[-1])
        },
        "regime_hint": regime,
        "headlines": news_titles()
    }
    os.makedirs("reports", exist_ok=True)
    with open("reports/weekly_insight.json","w",encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report
```

---

# 策略生成（LLM）提示模板

**prompts/strategy\_dev.md（節選）**

```
你是一位量化策略設計師。輸入是一份 JSON 週報（市場狀態、指標、regime_hint）。
請輸出「單一 Python 檔」的 backtrader 策略類別，檔名：StrategyCandidate.py。

要求：
- 僅用簡單、可解釋指標（例如 MA、RSI、BBands）。
- 參數不超過 6 個，並在 __init__ 中宣告。
- 交易邏輯需避免前視（不可用未來資料）。
- 考慮交易成本與滑點整合在 backtrader Cerebro 設定中。
- 需加入風控：固定停損（如8%）與 ATR 追蹤停損（二選一即可）。
- 必須有買進/賣出條件註解與 self.log()。
```

---

# 回測執行器（backtrader）

**backtest/bt\_runner.py（摘錄）**

```python
import backtrader as bt, pandas as pd, json, os, datetime as dt
from .metrics import summarize_metrics

class PandasDataTZ(bt.feeds.PandasData):
    params = (('datetime', None),)

def run_backtest(strategy_cls, df: pd.DataFrame, fees_bps=2, slip_bps=5, oos_months=6):
    # 切 OOS：最後 6 個月為外測，不參與訓練/參數尋優
    split_dt = df.index.max() - pd.DateOffset(months=oos_months)
    train_df = df[df.index <= split_dt]
    oos_df   = df[df.index >  split_dt]

    cerebro = bt.Cerebro()
    data = PandasDataTZ(dataname=train_df)
    cerebro.adddata(data)
    cerebro.addstrategy(strategy_cls)
    cerebro.broker.setcommission(commission=fees_bps/10000)
    cerebro.broker.set_slippage_perc(perc=slip_bps/10000)
    cerebro.broker.setcash(1_000_000)

    train_result = cerebro.run(maxcpus=1)[0]
    train_value  = cerebro.broker.getvalue()

    # OOS 單獨跑
    cerebro2 = bt.Cerebro(); cerebro2.addstrategy(strategy_cls)
    cerebro2.broker.setcommission(commission=fees_bps/10000)
    cerebro2.broker.set_slippage_perc(perc=slip_bps/10000)
    cerebro2.broker.setcash(1_000_000)
    cerebro2.adddata(PandasDataTZ(dataname=oos_df))
    oos_result = cerebro2.run(maxcpus=1)[0]
    oos_value  = cerebro2.broker.getvalue()

    metrics = summarize_metrics(train_df, oos_df, initial=1_000_000, train_end_value=train_value, oos_end_value=oos_value)
    return metrics
```

**backtest/metrics.py（簡要）**

```python
import numpy as np, pandas as pd, json, os

def sharpe(returns, rf=0.0):
    if returns.std() == 0: return 0.0
    return np.sqrt(252) * (returns.mean() - rf/252) / returns.std()

def max_drawdown(equity_curve):
    roll_max = equity_curve.cummax()
    dd = (equity_curve/roll_max - 1).min()
    return abs(float(dd))

def summarize_metrics(train_df, oos_df, initial, train_end_value, oos_end_value):
    # 這裡可擴充為逐日 NAV，暫以端點近似 + 交易點位回寫
    train_ret = (train_end_value/initial - 1.0)
    oos_ret   = (oos_end_value/initial - 1.0)
    # 假設你在策略裡有每日損益記錄，可換成真 returns
    dummy_daily = train_df['close'].pct_change().dropna()
    return {
        "train": {
            "ann_return": float(train_ret),
            "sharpe": float(sharpe(dummy_daily)),
            "mdd": float(max_drawdown((1+dummy_daily).cumprod()))
        },
        "oos": {
            "ann_return": float(oos_ret),
            "sharpe": float(sharpe(dummy_daily.tail(60))), # 佔位
            "mdd": float(max_drawdown((1+dummy_daily.tail(60)).cumprod()))
        }
    }
```

---

# 紙上交易帳戶（模擬交易）

**sim/paper\_broker.py（摘錄）**

```python
import pandas as pd, json, os, datetime as dt

class PaperBroker:
    def __init__(self, cash=1_000_000, fees_bps=2, slip_bps=5, log_path="logs/trades.csv"):
        self.cash = cash
        self.pos  = 0
        self.avg_cost = 0.0
        self.fees = fees_bps/10000
        self.slip = slip_bps/10000
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self.log_path = log_path
        if not os.path.exists(log_path):
            pd.DataFrame(columns=["time","side","qty","price","cash","pos","avg_cost"]).to_csv(log_path,index=False)

    def _exec(self, side, qty, price, ts):
        px = price * (1+self.slip if side=="buy" else 1-self.slip)
        cost = px*qty
        fee = cost*self.fees
        if side=="buy":
            assert self.cash >= cost+fee, "Insufficient cash"
            self.cash -= (cost+fee)
            self.avg_cost = (self.avg_cost*self.pos + cost)/(self.pos+qty) if self.pos>0 else px
            self.pos += qty
        else:
            assert self.pos >= qty, "Insufficient position"
            self.cash += (cost-fee)  # 收入
            self.pos  -= qty
            if self.pos==0: self.avg_cost = 0
        self._log(ts, side, qty, px)

    def _log(self, ts, side, qty, px):
        df = pd.read_csv(self.log_path)
        df.loc[len(df)] = [ts, side, qty, px, self.cash, self.pos, self.avg_cost]
        df.to_csv(self.log_path, index=False)

    def buy(self, qty, price, ts):  self._exec("buy", qty, price, ts)
    def sell(self, qty, price, ts): self._exec("sell", qty, price, ts)
```

**sim/live\_runner.py（日常執行）**

```python
import pandas as pd, importlib.util, datetime as dt
from .paper_broker import PaperBroker
from crew.tools import fetch_ohlcv

def load_strategy(path):
    spec = importlib.util.spec_from_file_location("StrategyCandidate", path)
    mod  = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.StrategyCandidate

def run_daily(symbol="0050.TW", strategy_path="reports/strategy_candidate.py"):
    df = fetch_ohlcv(symbol, years=1)  # 當日含近一年
    price = float(df['close'].iloc[-1])
    # 這裡簡化：由策略的 generate_signal(df) 回傳 {"signal":"buy/sell/hold", "size_pct":0.5}
    Strategy = load_strategy(strategy_path)
    sig = Strategy.generate_signal(df)  # 需在策略內提供此靜態方法 for 實盤/模擬
    broker = PaperBroker()
    qty = int((broker.cash * sig.get("size_pct",0.5)) / price)
    ts = str(df.index[-1])
    if sig["signal"] == "buy" and qty>0: broker.buy(qty, price, ts)
    if sig["signal"] == "sell" and broker.pos>0: broker.sell(broker.pos, price, ts)
```

---

# 策略模板（可被 LLM 改寫）

**strategies\_library/ma\_rsi\_template.py（可讀/可改）**

```python
import pandas as pd, numpy as np

class StrategyCandidate:
    params = dict(fast=20, slow=60, rsi_n=14, rsi_lo=30, rsi_hi=70, size_pct=0.6, stop_loss=0.08)

    def __init__(self): pass

    @staticmethod
    def generate_signal(df: pd.DataFrame):
        px = df['close']
        ma_fast = px.rolling(StrategyCandidate.params['fast']).mean()
        ma_slow = px.rolling(StrategyCandidate.params['slow']).mean()
        rsi = StrategyCandidate._rsi(px, StrategyCandidate.params['rsi_n'])
        cross_up = (ma_fast.iloc[-2] <= ma_slow.iloc[-2]) and (ma_fast.iloc[-1] > ma_slow.iloc[-1])
        cross_dn = (ma_fast.iloc[-2] >= ma_slow.iloc[-2]) and (ma_fast.iloc[-1] < ma_slow.iloc[-1])

        if cross_up and rsi.iloc[-1] > StrategyCandidate.params['rsi_n']:
            return {"signal":"buy","size_pct":StrategyCandidate.params['size_pct']}
        if cross_dn or rsi.iloc[-1] > StrategyCandidate.params['rsi_hi']:
            return {"signal":"sell","size_pct":StrategyCandidate.params['size_pct']}
        return {"signal":"hold"}

    @staticmethod
    def _rsi(series, n=14):
        delta = series.diff()
        up = delta.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
        dn = -delta.clip(upper=0).ewm(alpha=1/n, adjust=False).mean()
        rs = up/dn.replace(0,np.nan)
        return 100 - (100/(1+rs))
```

> 實務上由 **策略開發師 Agent（LLM）** 讀取週報、參照模板，自動生成新的 `StrategyCandidate.py`（參數、條件、風控邏輯都可被 LLM 調整）。

---

# CrewAI 代理與任務

**crew/agents.py（精簡）**

```python
from crewai import Agent
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

market_analyst = Agent(
    role="市場分析師", goal="輸出 0050 週度市場觀察",
    backstory="善用 yfinance 與技術指標",
    llm=llm, tools=[], verbose=True)

strategy_dev = Agent(
    role="策略開發師", goal="產生 backtrader 策略碼",
    backstory="擅長將 regime 與模板結合",
    llm=llm, tools=[], verbose=True)

backtest_engineer = Agent(
    role="回測工程師", goal="嚴格回測與產出報告",
    backstory="重現性與反過度擬合至上",
    llm=llm, tools=[], verbose=True)

risk_sim = Agent(
    role="風控與模擬交易員", goal="部署與執行紙上交易",
    backstory="紀律執行者", llm=llm, tools=[], verbose=True)
```

**crew/tasks.py（重點工作流）**

```python
from crewai import Task, Crew
from .agents import market_analyst, strategy_dev, backtest_engineer, risk_sim
from .tools import weekly_insight, fetch_ohlcv, add_indicators
from backtest.bt_runner import run_backtest

def weekly_pipeline():
    # Task1: 週報
    report = weekly_insight("0050.TW", years=3)

    # Task2: 生成策略碼（用 LLM 讀 prompts/strategy_dev.md 與 report）
    # 這裡簡化為直接複製模板或載入上一版策略並小幅調參
    import shutil
    shutil.copyfile("strategies_library/ma_rsi_template.py","reports/strategy_candidate.py")

    # Task3: 回測
    import importlib.util, pandas as pd
    df = add_indicators(fetch_ohlcv("0050.TW", years=3))
    spec = importlib.util.spec_from_file_location("StrategyCandidate","reports/strategy_candidate.py")
    mod  = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    metrics = run_backtest(mod.StrategyCandidate, df)

    # Task4: 風控門檻
    import json
    with open("config/risk.yaml") as f:
        import yaml; risk = yaml.safe_load(f)
    th = risk["deploy_thresholds"]
    ok = (metrics["oos"]["sharpe"] >= th["min_sharpe"]
          and metrics["oos"]["mdd"] <= th["max_mdd"])
    decision = {"accept": bool(ok), "metrics": metrics}
    with open("reports/deployment_decision.json","w") as f: json.dump(decision,f,indent=2)
    return decision
```

**crew/run\_weekly.py**

```python
if __name__ == "__main__":
    decision = weekly_pipeline()
    print("DEPLOY:", decision["accept"])
```

---

# 自我學習與防過擬合

* **資料切分**：固定留出 **最近 6 個月**做 OOS；週週更新訓練窗與 OOS 窗，視為**走勢外推**。
* **簡單優先**：限制策略參數 ≤ 6，避免複雜規則樹。
* **多策略競賽**：保留近 6–12 週「上線策略」與其 OOS 表現；**僅根據後續 OOS 表現打分**（Sharpe×穩定度×風險成本），形成**策略池加權投票**（也可只選 Top1）。
* **成本與滑點**：在回測與模擬中一體化（`commission + slippage`）。
* **檢查清單**：

  * 無前視（嚴禁用當日收盤後數據下單的假設）
  * 交易頻率與換手受限（避免把雜訊當訊號）
  * 報告必含：`ann_return / sharpe / mdd / winrate / turnover / trades`
* **回饋閉環**：未通過的策略，將**失敗原因（如過度交易、高 MDD、低勝率）**以標準化 JSON 回饋給 LLM，下次生成策略時加入**懲罰條款**（例如「降低參數自由度、引入持有期約束」）。

---

# 任務排程

**sim/scheduler.py**

```python
from apscheduler.schedulers.blocking import BlockingScheduler
from crew.run_weekly import weekly_pipeline
from sim.live_runner import run_daily

sch = BlockingScheduler(timezone="Asia/Taipei")

# 每週六 09:00 跑學習（台北時間）
@sch.scheduled_job('cron', day_of_week='sat', hour=9)
def weekly_job(): weekly_pipeline()

# 交易日收盤後 14:00 更新信號/執行紙上交易（台北時間）
@sch.scheduled_job('cron', day_of_week='mon-fri', hour=14)
def daily_job(): run_daily()

if __name__ == "__main__":
    sch.start()
```

---

# Docker 與部署

**requirements.txt（關鍵）**

```
crewai
langchain-openai
yfinance
pandas
numpy
backtrader
vectorbt
matplotlib
beautifulsoup4
requests
pyyaml
apscheduler
```

**Dockerfile（簡化）**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
ENV TZ=Asia/Taipei
CMD ["python","sim/scheduler.py"]
```

---

# 安全與治理建議

* **金鑰管理**：如用 TEJ/新聞 API，放在 `.env`，不要硬寫入程式。
* **LLM 產碼安全**：用 `python_sanity_checker`（靜態掃描）阻擋 `os.system` / 檔案刪除等危險語句。
* **審計**：所有自動決策（策略選擇、交易執行）都要落地到 `logs/` & `reports/`，便於溯源。
* **回滾**：若連續 N 日 OOS performance < 門檻 → 自動降級為「持有或空倉」模式。

---

# 立即啟動（本機示範順序）

1. `python crew/run_weekly.py` → 產出策略與回測報告與部署決策
2. `python sim/live_runner.py` → 以最新資料執行一次紙上交易
3. 長期運行：`python sim/scheduler.py` 或用 Docker Compose/系統服務守護

---

想不想要我幫你把**策略生成提示模板**加上更具體的**回饋規則**（例如自動懲罰高換手或高 MDD），或是把 TEJ API 的資料拉取與欄位對應範例也補上？

---

**這是一般資訊，不是投資建議。若需個人化建議，請諮詢持牌專業人士。**
