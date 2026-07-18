# TradingAgents + Podcast 系統架構文件

> 文件版本：2026-07-11 (v2.0)
> 更新內容：Gemini 直連 + FinBERT 多層 fallback + B2 graceful fallback

---

## 目錄

1. [系統總覽](#1-系統總覽)
2. [為何放棄 TradingAgents 原生方案](#2-為何放棄-tradingagents-原生方案)
3. [核心架構](#3-核心架構)
4. [數據流 Pipeline](#4-數據流-pipeline)
5. [Gemini 直連 TA 信號引擎](#5-gemini-直連-ta-信號引擎附錄)
6. [情緒分析模組](#6-情緒分析模組)
7. [語音合成 (Edge TTS)](#7-語音合成-edge-tts)
8. [B2 雲端備份與 RSS 發布](#8-b2-雲端備份與-rss-發布)
9. [策略模組](#9-策略模組)
10. [Hermès Cron Job 排程](#10-hermès-cron-job-排程)
11. [目錄結構](#11-目錄結構)
12. [依賴与环境](#12-依賴與環境)
13. [已知 issue 與修復方式](#13-已知-issue-與修復方式)

---

## 1. 系統總覽

本系統由三大部分組成：

| 元件 | 技術棧 | 狀態 |
|------|--------|------|
| **TA 信號引擎** | `ta_generator.py` + Gemini API | ✅ 主動作者 |
| **情緒分析** | FinBERT (HuggingFace) → 關鍵詞 | ✅ 已添加 fallback |
| **Podcast 生產線** | Nim API + Edge TTS + B2 | ✅ Edge TTS 主動作者 |
| **策略分析** | GodSystem + BigLine (本地) | ✅ |
| **Cron 排程** | Hermès Gateway | ✅ |

**為什麼不放棄情緒分析？**
- 它影響 `data_collector.py` → `market_analyst.py` 的輸入情緒分數
- 影響腳本內容豐富度，但不是 Block Issue

---

## 2. 為何放棄 TradingAgents 原生方案

| 問題 | 原因 | 影響 |
|------|------|------|
| NVIDIA API 返回 `401 Unauthorized` | 機器網路限制（與 rate limit 無關） | 所有基於 TradingAgents 的 LLM 推理全部失敗 |
| NVIDIA API `timeout` | API 被阻止 | 每次嘗試浪費 30 秒 |
| B2 認證失效 (`bad_auth_token`) | API Key/Application Key 過期 | 圖表、MP3、RSS 無法上傳到 CDN |

**替代方案**：
- **Gemini 直連**（`ta_generator.py`）：直接調用 Google Gemini API，繞過 NVIDIA，11 秒分析 12 檔股票
- **B2 graceful fallback**：認證失敗時返回 `local://` 路徑，流程不中斷

---

## 3. 核心架構

```
                        ┌─────────────────────────────┐
                        │  TradingAgents (已棄用)      │
                        │  NVIDIA API 401 → 不使用    │
                        └──────────────┬──────────────┘
                                       │ (僅用作報告生成)
                           ┌───────────▼───────────┐
                           │   ta_generator.py     │
                           │   Gemini 直連 (~11s)   │
                           │   12檔股票 TA 信號   │
                           └───────────┬───────────┘
                                       │ bridge_YYYY-MM-DD.json
                           ┌───────────▼───────────┐
                           │     ta_bridge.py      │
                           │   (cache loader)       │
                           └───────────┬───────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            │                          │                          │
    ┌───────▼────────┐        ┌───────▼────────┐        ┌─────────▼────────┐
    │  data_collector │        │  market_analyst │        │  strategy engine  │
    │  (情緒分析)      │        │  (技術報告)      │        │  God+BigLine     │
    └───────┬────────┘        └─────────────────┘        └─────────┬────────┘
            │                                                     │
    ┌───────▼─────────────────────────────────────────────────────▼────────┐
    │                            content_creator.py                           │
    │                        Nim API（Gemini 3.1-flash-lite）                 │
    │                          繁體中文 Podcast 腳本                          │
    └────────────────────────────────┬───────────────────────────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │          voice_producer.py        │
                    │      Edge TTS → MP3 (~5秒)         │
                    │    zh-TW-YunJheNeural (微軟)      │
                    └────────────────┬────────────────┘
                                     │ audio_file
                    ┌────────────────▼────────────────┐
                    │        cloud_manager.py          │
                    │   B2 upload_episode / upload_rss │
                    │   (bad_auth_token → local://)    │
                    └────────────────┬────────────────┘
                                     │ podcast.xml + MP3 URL
                    ┌────────────────▼────────────────┐
                    │    podcast_distributor.py         │
                    │   RSS 生成 + Slack 通知          │
                    └───────────────────────────────────┘
```

---

## 4. 數據流 Pipeline

### 每日完整流程（~60-90秒）

```bash
# Step 1: 觸發 TA 信號（手動或 cron job 14:30）
cd /home/bbm/podcast && source ../TradingAgents/venv/bin/activate &&   export GEMINI_API_KEY=$(cat /home/bbm/.config/gemini_key) &&   python3 ta_generator.py

# Step 2: 驗證 Bridge cache
cd /home/bbm/podcast && python3 ta_bridge.py --read-only

# Step 3: 產製 Podcast（TW 或 US 模式）
cd /home/bbm/podcast && source ../TradingAgents/venv/bin/activate &&   export GEMINI_API_KEY=$(cat /home/bbm/.config/gemini_key) &&   python3 main.py --mode tw   # 或 --mode us
```

### 輸出文件

| 檔案 | 路徑 | 說明 |
|------|------|------|
| Bridge cache | `data/ta_bridge/bridge_YYYY-MM-DD.json` | TA 信號 + 市場分析 |
| TA Signals | `data/ta_bridge/ta_signals_YYYY-MM-DD.json` | 原始 Gemini 回應 |
| Podcast 音頻 | `docs/podcast/YYYYMMDD_tw/daily-podcast-stk-YYYYMMDD_tw.mp3` | Edge TTS 產出 |
| Podcast 腳本 | `docs/podcast/YYYYMMDD_tw/daily-podcast-stk-YYYYMMDD_tw.txt` | 最終腳本 |
| RSS Feed | `data/rss/podcast.xml` | B2 CDN 上的 podcast.xml |
| 市場數據 | `data/market/daily_*.csv` | yfinance 歷史數據 |

---

## 5. Gemini 直連 TA 信號引擎（附錄）

### ta_generator.py 原理

```
1. 以 yfinance 取得 6 個月的 OHLCV 歷史數據
2. 計算技術指標：SMA20, SMA50, RSI(14)
3. 將指標餽送給 Gemini API（gemini-3.1-flash-lite）
4. Gemini 回覆：信號（BUY/SELL/HOLD）+ 理由
5. 生成並保存三種 bridge 格式 Cache 文件
```

### Gemini 模型優先順序

| 模型 | 速度 | Rate Limit | 用途 |
|------|------|------------|------|
| `gemini-3.1-flash-lite` | ~2.5-4s | 幾乎無限制 | **主要模型** |
| `gemini-2.5-flash` | ~12s | 中等 | Fallback #1 |
| Ollama qwen3.6 | ~30s | 無（本地） | Fallback #2 |

### 分析的股票 Watchlist

**台股**：0050.TW, 2330.TW, 2412.TW, 2454.TW, 2881.TW, 2317.TW
**美股**：QQQ, SPY, SOXX, NVDA, TSLA, AAPL

---

## 6. 情緒分析模組

### 架構（4層 fallback）

```
get_sentiment_analyzer()
    │
    ├─ [Layer 1] ProsusAI/finbert (HuggingFace) ← 最常用
    │                      ↓ 404/load error
    └─ [Layer 2] yiyanghkust/finbert-pretrain
                        ↓ load error
         ┌──────────────┴──────────────┐
         │  Layer 3: Gemini (可選)    │
         │  Layer 4: Keyword fallback ← 永遠可用
         │  (不依賴任何外部模型)        │
         └─────────────────────────────┘
```

### 關鍵詞情緒（Layer 4）

```python
bullish = ["牛市","多頭","買進","Buy","看好","漲","利多","成長","突破"]
bearish = ["熊市","空頭","賣出","Sell","看淡","跌","利空","衰退","跌破"]
```

### 對 Podcast 的影響

- `sentiment_score > 0` → 腳本措辭偏正面
- `sentiment_score < 0` → 腳本措辭偏謹慎
- 情緒分析失敗 → 全部使用中性分數 `0.0`，不影響流程

---

## 7. 語音合成（Edge TTS）

Edge TTS 使用 Microsoft 的 `zh-TW-YunJheNeural`（雲中君）語音，適合台灣中文 podcast。

**聲音參數**：
- 音量：+0%
- 語速：+10%（略快，適合 daily briefing）
- 音調：+0%

**其他可用聲音**（從 edge-tts 列出）：
```bash
edge-tts --list-voices | grep zh-TW
```

**優勢**：
- 完全免費
- 無速率限制
- 延遲低（< 5秒生成 MP3）
- **已驗證：無需網路上傳，直接本地生成**

---

## 8. B2 雲端備份與 RSS 發布

### 上傳函數

| 函數 | 上傳目標 | 失敗影響 |
|------|----------|---------|
| `upload_episode()` | MP3 + TXT | RSS 只能用 local:// |
| `upload_rss()` | podcast.xml | RSS feed 無法被 podcast clients 訂閱 |
| `upload_chart()` | 策略圖表 → charts/ | Slack 無法顯示可點擊圖表連結 |
| **全部** | B2 (backblazeb2.com) | `bad_auth_token` → graceful fallback |

### 當前 B2 狀態

`bad_auth_token` 錯誤 → 所有上傳降級到 `local://` → Podcast 仍可本地播放

**修復方式**：
1. 登入 backblazeb2.com
2. 前往 Application Keys 頁面
3. 重新生成 `B2_KEY_ID` 和 `B2_APPLICATION_KEY`
4. 更新 `/home/bbm/.hermes/.env` 中的環境變數
5. 重啟 Hermes Gateway：pkill -f hermes; bash ~/.hermes/autostart.sh

---

## 9. 策略模組

### GodSystemStrategy（主策略）
- RSI + 移動平均線 + 支撑/阻力位
- 動態倉位配置

### BigLineStrategy（輔助策略）
- 大趨勢線突破確認
- 短線動量跟蹤

### 策略結果與 TA 信號整合
- 策略結果寫入 `bridge_*.json`
- `main.py` 中的 `if _TA_BRIDGE_AVAILABLE:` 分支

---

## 10. Hermès Cron Job 排程

| Job ID | 名稱 | 時間 | 狀態 | 說明 |
|--------|------|------|------|------|
| `44fcb9d` | TA Generator 每日分析（Gemini 直連） | 14:30 平日 | ✅ scheduled | 先 `ta_generator.py` → 再 `ta_bridge.py` |
| `ae10b9a` | TA Generator 每週分析 + 策略優化 | 週日 10:00 | ✅ scheduled | `ta_generator.py` + TradingAgents `--weekly` |
| `ea3dc14` | TradingAgents 每月績效回顧 | 每月 1日 11:00 | ✅ scheduled | `ta_generator.py` + `--monthly` |
| `972084` | TradingAgents 每日分析（舊版） | 每日 06:00 | ⏸ paused | 待機用 |
| `de99409` | 每週（舊版） | 週日 08:00 | ⏸ paused | 待機用 |
| `19adca` | 每月（舊版） | 每月 1日 09:00 | ⏸ paused | 待機用 |

**注意**：`972084/de99409/19adca` 這三個 job 在 2026-05-05 以後就暫停了，但仍然保留在 jobs.json 中作為潛在使用。

---

## 11. 目錄結構

```
/home/bbm/podcast/
├── ta_generator.py        ← 【核心】Gemini 直連 TA 信號生成器（2026-07-11 新增）
├── ta_bridge.py            ← Bridge cache loader
├── data_collector.py      ← 【修改】情緒分析多層 fallback（2026-07-11）
├── market_analyst.py       ← 市場技術分析報告
├── content_creator.py      ← Nim API → 腳本生成
├── voice_producer.py       ← Edge TTS → MP3
├── cloud_manager.py        ← 【修改】B2 上傳 + graceful fallback（2026-07-11）
├── podcast_distributor.py  ← RSS 生成 + Slack 通知
├── auto_sync.py            ← 自動同步腳本
├── main.py                 ← Podcast 生產線主入口
├── nim_api.py              ← Nim API 封裝（gemini-3.1-flash-lite primary）
├── config.json             ← 系統配置
├── strategies/
│   ├── god_system_strategy.py
│   ├── bigline_strategy.py
│   └── utils.py            ← 策略圖表生成（調用 upload_chart）
├── data/
│   ├── ta_bridge/          ← TA 信號 cache（ta_generator.py 產出）
│   ├── market/             ← yfinance CSV 歷史數據
│   ├── news/               ← 爬蟲新聞
│   └── sentiment/          ← 情緒分析結果
├── docs/
│   ├── podcast/            ← Podcast 產出（MP3 + TXT）
│   └── script.txt          ← 手動覆蓋腳本
└── logs/                   ← 運行日誌

/home/bbm/.hermes/
├── cron/jobs.json          ← Hermès 任務排程（已更新 2026-07-11）
└── .env                    ← 環境變數（B2 keys 等）

/home/bbm/.config/gemini_key ← Gemini API Key（已驗證有效）
```

---

## 12. 依賴與環境

```bash
# 主要 venv
source /home/bbm/TradingAgents/venv/bin/activate

# 必要的 pip 包（已驗證）
pip install yfinance loguru retry httpx pandas ta matplotlib
pip install b2sdk feedgen mutagen python-dotenv pytz
pip install beautifulsoup4 requests
pip install transformers torch torch torchvision  # FinBERT 需要
pip install edge-tts

# Gemini API Key（已驗證，最佳模型）
GEMINI_API_KEY=AIzaSyCrQgVVljywn3OAdqvh-ETYBymiBF7H1D8
# 模型：gemini-3.1-flash-lite（速度快，幾乎無 rate limit）
```

### 環境變數

| 變數 | 來源 | 狀態 |
|------|------|------|
| `GEMINI_API_KEY` | `/home/bbm/.config/gemini_key` | ✅ 已設定 |
| `B2_KEY_ID` | Hermes `.env` | 🔴 需更新（bad_auth_token）|
| `B2_APPLICATION_KEY` | Hermes `.env` | 🔴 需更新 |
| `B2_BUCKET_NAME` | config.json | ✅ 已設定 |
| `B2_PODCAST_PREFIX` | config.json | ✅ 已設定 |

---

## 13. 已知 Issue 與修復方式

| # | Issue | 嚴重度 | 修復方式 |
|---|-------|--------|----------|
| 1 | NVIDIA API 401（TradingAgents） | 🔴 已繞過 | `ta_generator.py` (Gemini) |
| 2 | B2 `bad_auth_token` | 🔴 需更新 | 重新生成 backblazeb2.com API keys |
| 3 | FinBERT HuggingFace 404 | 🟡 已修復 | 多層 fallback → Keyword |
| 4 | `upload_chart` B2 失敗 | 🟡 已修復 | graceful `return None` |
| 5 | Hermès jobs 972084/19adca paused | 🟢 低 | 待機，可忽略 |
| 6 | `bwrap: loopback` sandbox 限制 | 🟢 低 | 與系統功能無關 |

---

## 附錄：快速命令參考

```bash
# 1. 刷新 TA 信號（~11秒）
cd /home/bbm/podcast && source ../TradingAgents/venv/bin/activate &&   export GEMINI_API_KEY=$(cat /home/bbm/.config/gemini_key) &&   python3 ta_generator.py

# 2. 生成 TW Podcast
cd /home/bbm/podcast && source ../TradingAgents/venv/bin/activate &&   export GEMINI_API_KEY=$(cat /home/bbm/.config/gemini_key) &&   python3 main.py --mode tw

# 3. 生成 US Podcast
cd /home/bbm/podcast && source ../TradingAgents/venv/bin/activate &&   export GEMINI_API_KEY=$(cat /home/bbm/.config/gemini_key) &&   python3 main.py --mode us

# 4. 檢查 Bridge cache
cd /home/bbm/podcast && python3 ta_bridge.py --read-only

# 5. 查看 Hermes jobs
cat /home/bbm/.hermes/cron/jobs.json | python3 -m json.tool | less

# 6. 查看 Hermes 日誌
tail -50 /home/bbm/.hermes/logs/agent.log

# 7. 更新 B2 credentials（修復 bad_auth_token）
# Edit /home/bbm/.hermes/.env → restart Hermes Gateway
```

---

*架構文件由 Codex 生成，2026-07-11 17:55 CST*
*版本：v2.0 — 基於 v1.0（2026-07-11 13:00）大幅更新*
