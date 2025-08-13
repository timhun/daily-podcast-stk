### 步驟 1: 理解系統概述
在開始實施前，讓我們回顧系統的核心：這是一個基於 CrewAI 框架的 AI Agent 團隊，專注於台灣 0050 ETF 的模擬交易系統。系統不是固定策略，而是自我學習的閉環，包括市場分析、策略生成、回測驗證和模擬交易。團隊有 4 個 Agent：
- **市場分析師 (Market Analyst)**: 收集數據並計算指標。
- **策略開發師 (Strategy Developer)**: 生成新策略。
- **回測工程師 (Backtesting Engineer)**: 驗證策略績效。
- **風控與模擬交易員 (Risk & Simulation Agent)**: 決定部署並執行模擬交易。

系統分為兩個階段：
- **Phase 1**: 每週末運行，生成並驗證新策略。
- **Phase 2**: 每個交易日運行，執行模擬交易。

我們將使用 Python 實現，依賴 CrewAI、LangChain (用於 LLM)、yfinance (數據)、backtrader (回測)等庫。假設你使用 OpenAI 的 GPT-4o 作為 LLM（可替換為 Grok API，如果可用）。

**注意**:
- 這是模擬系統，非真實交易。勿用於真錢。
- 需要 API 鑰匙：OpenAI API key。
- 運行環境：Python 3.10+，在 Jupyter Notebook 或 VS Code 中測試最佳。
- 如果遇到錯誤，檢查依賴版本或 API 配額。

### 步驟 2: 設定開發環境
1. **安裝 Python**: 確保你有 Python 3.12+。下載自 [python.org](https://www.python.org/)。
2. **創建虛擬環境** (推薦，避免衝突):
   ```
   python -m venv crewai-trading-env
   source crewai-trading-env/bin/activate  # Mac/Linux
   # 或 Windows: crewai-trading-env\Scripts\activate
   ```
3. **安裝依賴庫**:
   運行以下 pip 命令（一次安裝所有）:
   ```
   pip install crewai crewai-tools langchain langchain-openai yfinance pandas numpy backtrader matplotlib requests beautifulsoup4
   ```
   - **crewai**: AI Agent 框架。
   - **langchain-openai**: 用於 LLM 整合。
   - **yfinance**: 獲取 0050 數據 (ticker: 0050.TW)。
   - **backtrader**: 回測引擎。
   - **其他**: 數據處理和新聞抓取。

4. **設定 API 鑰匙**:
   - 註冊 OpenAI 帳號，獲取 API key。
   - 在終端機設定環境變量:
     ```
     export OPENAI_API_KEY='your_openai_api_key_here'
     ```
     或在代碼中直接設定 `os.environ["OPENAI_API_KEY"] = 'your_key'`。

### 步驟 3: 定義自訂工具 (Custom Tools)
工具是 Agent 的“武器”。我們需要定義它們來處理數據、指標計算、回測等。

創建一個 Python 檔案 `tools.py`，並輸入以下代碼：

```python
from crewai_tools import BaseTool
import yfinance as yf
import pandas as pd
import numpy as np
import backtrader as bt
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import io
import logging

class YFinanceDataTool(BaseTool):
    name = "YFinance Data Fetcher"
    description = "Fetches historical OHLCV data for 0050.TW using yfinance."

    def _run(self, period="2y"):
        data = yf.download("0050.TW", period=period)
        return data.to_json()

class IndicatorCalculatorTool(BaseTool):
    name = "Technical Indicator Calculator"
    description = "Calculates technical indicators like MA, RSI, MACD from provided data."

    def _run(self, data_json, indicators=["MA", "RSI", "MACD"]):
        df = pd.read_json(io.StringIO(data_json))
        df.index = pd.to_datetime(df.index)
        results = {}

        if "MA" in indicators:
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            results["MA"] = df[['MA5', 'MA20']].tail(10).to_json()

        if "RSI" in indicators:
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            results["RSI"] = df['RSI'].tail(10).to_json()

        if "MACD" in indicators:
            ema12 = df['Close'].ewm(span=12, adjust=False).mean()
            ema26 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = ema12 - ema26
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            results["MACD"] = df[['MACD', 'Signal']].tail(10).to_json()

        return str(results)

class NewsScraperTool(BaseTool):
    name = "News Scraper"
    description = "Scrapes news headlines related to Taiwan 50 or TaiEX."

    def _run(self, keywords="台灣50 台股權值股 國發會景氣燈號"):
        url = f"https://www.google.com/search?q={keywords}&tbm=nws"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        headlines = [h.text for h in soup.find_all('h3')]
        return "\n".join(headlines[:5])  # 限制為前 5 條

class BacktraderRunnerTool(BaseTool):
    name = "Backtrader Strategy Tester"
    description = "Runs backtest on provided strategy code using historical data."

    def _run(self, strategy_code, data_json, start_date, end_date):
        df = pd.read_json(io.StringIO(data_json))
        df.index = pd.to_datetime(df.index)
        data_feed = bt.feeds.PandasData(dataname=df.loc[start_date:end_date])

        exec(strategy_code, globals())  # 執行策略代碼以定義類別 (假設類別名為 GeneratedStrategy)

        cerebro = bt.Cerebro()
        cerebro.adddata(data_feed)
        cerebro.addstrategy(GeneratedStrategy)
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.broker.setcash(1000000)
        results = cerebro.run()

        strat = results[0]
        sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
        drawdown = strat.analyzers.drawdown.get_analysis()['max']['drawdown']
        trades = strat.analyzers.trades.get_analysis()
        win_rate = (trades['won']['total'] / trades['total']['total']) * 100 if trades['total']['total'] > 0 else 0
        annualized_return = (cerebro.broker.getvalue() / 1000000 - 1) * 100  # 簡化計算

        # 產生圖表 (選用)
        fig = cerebro.plot(style='candlestick')[0][0]
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        # 在真實中，可儲存圖檔；這裡返回文字報告

        return f"Sharpe Ratio: {sharpe:.2f}, Max Drawdown: {drawdown:.2f}%, Win Rate: {win_rate:.2f}%, Annualized Return: {annualized_return:.2f}%"

class PaperTradingSimulator:
    def __init__(self, initial_cash=1000000):
        self.cash = initial_cash
        self.position = 0
        self.trades = []
        logging.basicConfig(filename='trading_log.txt', level=logging.INFO)

    def buy(self, price, shares):
        cost = price * shares
        if self.cash >= cost:
            self.cash -= cost
            self.position += shares
            logging.info(f"Buy: {shares} shares at {price}")
            self.trades.append({"action": "buy", "price": price, "shares": shares})

    def sell(self, price, shares):
        if self.position >= shares:
            revenue = price * shares
            self.cash += revenue
            self.position -= shares
            logging.info(f"Sell: {shares} shares at {price}")
            self.trades.append({"action": "sell", "price": price, "shares": shares})

    def get_portfolio_value(self, current_price):
        return self.cash + self.position * current_price

class SimulationTool(BaseTool):
    name = "Paper Trading Simulator"
    description = "Simulates trades based on strategy signals."
    simulator = PaperTradingSimulator()  # 共享實例以維持狀態

    def _run(self, action, price, shares):
        if action == "buy":
            self.simulator.buy(price, shares)
        elif action == "sell":
            self.simulator.sell(price, shares)
        return f"Portfolio Value: {self.simulator.get_portfolio_value(price)}"
```

**測試工具**: 在終端機運行 `python tools.py` 確保無錯誤（它不會輸出，但會載入類別）。

### 步驟 4: 定義 Agent、Task 和 Crew
創建主檔案 `main.py`，輸入以下代碼。這整合了 Agent 和 Task。

```python
import os
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from tools import (YFinanceDataTool, IndicatorCalculatorTool, NewsScraperTool,
                   BacktraderRunnerTool, SimulationTool)

# 設定 LLM
os.environ["OPENAI_API_KEY"] = "your_openai_api_key_here"  # 如果未設環境變量
llm = ChatOpenAI(model="gpt-4o", temperature=0.5)  # temperature 控制創意度

# 定義 Agent
market_analyst = Agent(
    role="Market Analyst",
    goal="Collect and interpret 0050 data for insights.",
    backstory="Expert in data analysis for trading signals.",
    tools=[YFinanceDataTool(), IndicatorCalculatorTool(), NewsScraperTool()],
    llm=llm,
    verbose=True
)

strategy_developer = Agent(
    role="Strategy Developer",
    goal="Generate trading strategies based on market insights.",
    backstory="Creative quant who innovates strategies.",
    tools=[],
    llm=llm,
    verbose=True
)

backtesting_engineer = Agent(
    role="Backtesting Engineer",
    goal="Validate strategies with backtests.",
    backstory="Rigorous tester to avoid overfitting.",
    tools=[BacktraderRunnerTool()],
    llm=llm,
    verbose=True
)

risk_simulation_agent = Agent(
    role="Risk & Simulation Trader",
    goal="Deploy and simulate trades with risk control.",
    backstory="Disciplined executor for simulated trading.",
    tools=[SimulationTool()],
    llm=llm,
    verbose=True
)

# 定義 Task - Phase 1 (每週)
task1_data_insight = Task(
    description="Fetch 0050 data (2y), calculate MA, RSI, MACD, scrape news, summarize market features.",
    expected_output="JSON report: {'data_summary': ..., 'indicators': ..., 'news': ..., 'features': 'e.g., high volatility'}",
    agent=market_analyst
)

task2_strategy_generation = Task(
    description="Based on report, generate a backtrader strategy code. E.g., if trending, MA crossover; if ranging, Bollinger reversal.",
    expected_output="Python code string: class GeneratedStrategy(bt.Strategy): ...",
    agent=strategy_developer,
    context=[task1_data_insight]
)

task3_backtesting = Task(
    description="Backtest strategy on past 3y data (exclude last 6m). Use start_date='2020-01-01', end_date='2025-02-01' (adjust to current).",
    expected_output="JSON: {'sharpe': ..., 'drawdown': ..., 'win_rate': ..., 'return': ...}",
    agent=backtesting_engineer,
    context=[task2_strategy_generation]
)

task4_deployment_decision = Task(
    description="If sharpe > 1.0 and drawdown < 20%, deploy; else feedback to developer.",
    expected_output="Decision: 'Deploy' or 'Feedback: reasons'",
    agent=risk_simulation_agent,
    context=[task3_backtesting]
)

# 創建 Phase 1 Crew
weekly_crew = Crew(
    agents=[market_analyst, strategy_developer, backtesting_engineer, risk_simulation_agent],
    tasks=[task1_data_insight, task2_strategy_generation, task3_backtesting, task4_deployment_decision],
    process=Process.sequential,
    verbose=2,
    memory=True  # 啟用記憶體以支持反饋閉環
)

# 定義 Task - Phase 2 (每日)
task5_daily_trading = Task(
    description="Fetch today's 0050 data, apply deployed strategy, simulate buy/sell, log trades.",
    expected_output="Daily log: trades and portfolio value.",
    agent=risk_simulation_agent
)

# Phase 2 Crew (單一 Agent)
daily_crew = Crew(
    agents=[risk_simulation_agent],
    tasks=[task5_daily_trading],
    process=Process.sequential,
    verbose=2
)

# 運行示例 (在 main.py 底部添加)
if __name__ == "__main__":
    print("Running Weekly Crew...")
    weekly_result = weekly_crew.kickoff()
    print(weekly_result)
    
    # 手動運行每日: daily_crew.kickoff() (在交易日執行)
```

**調整**:
- 在 task3 中，調整日期為過去 3 年（例如，從今天減 3 年到減 6 月）。
- 策略生成中，確保輸出是有效的 backtrader Strategy 類別（LLM 會生成）。

### 步驟 5: 實現自我學習閉環
- 在 task4，如果未部署，反饋會儲存在 Crew 的記憶體中（memory=True）。
- 下次運行 weekly_crew 時，strategy_developer 會看到先前反饋（透過 context）。
- 為了持久化，使用檔案儲存反饋：
  - 在 task4 後，添加代碼儲存結果到 JSON 檔。
  - 下次載入作為輸入。

例如，在 main.py 添加：
```python
import json

# 在 kickoff 後
with open('feedback.json', 'w') as f:
    json.dump(weekly_result, f)

# 下次運行前載入
with open('feedback.json', 'r') as f:
    previous_feedback = json.load(f)
# 傳給 task2 的 description: "... and consider previous feedback: {previous_feedback}"
```

### 步驟 6: 測試與運行系統
1. **測試 Phase 1**:
   - 運行 `python main.py`。
   - 預期輸出：Agent 逐步執行，生成報告、策略、回測結果、決策。
   - 如果錯誤：檢查 LLM 輸出（verbose=True 會顯示），確保策略代碼有效（可能需手動調整 LLM prompt）。

2. **測試 Phase 2**:
   - 註解掉 weekly 部分，運行 daily_crew.kickoff()。
   - 檢查 trading_log.txt 檔案以查看模擬交易記錄。

3. **自動化**:
   - 使用 cron job (Linux/Mac) 或 Task Scheduler (Windows) 排程：
     - 每週日: python main.py --phase1
     - 每個交易日: python main.py --phase2
   - 添加命令列引數解析（使用 argparse）來切換階段。

4. **除錯與優化**:
   - **常見問題**: yfinance 數據失敗（檢查網路）；LLM 生成無效代碼（細調 prompt 或 temperature）。
   - **擴展**: 添加更多指標（KD, Bollinger）；整合真實時間數據（yfinance 的 interval="1d"）。
   - **監控**: 每週檢查回測報告，調整門檻（sharpe > 1.0）。
   - **成本**: LLM 呼叫有費用；測試時用小模型如 gpt-3.5-turbo。

### 步驟 7: 監控與迭代
- 運行 1-2 週，檢查 log 和績效。
- 如果策略勝率低，強化 task2 prompt： "避免過度擬合，使用簡單組合。"
- 加入 email 通知：使用 smtplib 寄送每日報告到 Tim.oneway@gmail.com（基於先前要求）。
- 升級：整合 Grok API 替換 OpenAI，為更智能的推理。

恭喜！現在你有一個完整的、可運行的系統。從步驟 2 開始執行，如果卡住，提供錯誤訊息我再幫忙調試。
