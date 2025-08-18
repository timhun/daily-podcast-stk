# 幫幫忙說財經科技投資 Podcast (daily-podcast-stk)

每天早上6點自動更新，涵蓋美股、ETF、比特幣、黃金、熱門股、AI、經濟新聞及投資金句。

## RSS 訂閱
- [Apple Podcasts](https://podcasts.apple.com/)
- [Spotify](https://podcasters.spotify.com/)

RSS連結：
daily-podcast-stk/
├── .github/
│   └── workflows/
│       ├── podcast_us.yml              # 美股 podcast 自動流程
│       └── podcast_tw.yml              # 台股 podcast 自動流程（你目前的主要流程）
│
├── docs/
│   └── podcast/
│       └── 20250729_tw/                # 每日台股節目資料夾（日期 + 模式）
│           ├── audio.mp3               # 語音音檔（Edge TTS）
│           ├── script.txt              # 播報逐字稿
│           ├── archive_audio_url.txt   # B2 連結
│           └── market_data_tw.json     # 台股市場資料（Grok 回傳 JSON）
│
├── prompt/
│   ├── tw.txt                          # 平日台股播報 Prompt 模板
│   ├── tw_weekend.txt                  # 週末台股播報 Prompt 模板
│   ├── us.txt                          # 美股播報 Prompt 模板
│   └── us_weekend.txt                  # 美股週末 Prompt（如有）
│
├── scripts/
│   ├── generate_script_tw.py           # 台股逐字稿腳本生成器（主腳本）
│   ├── fetch_tw_market_data_grok.py    # 呼叫 Grok API，產出 market_data_tw.json
│   ├── analyze_bullish_signal_from_prompt.py  # 解析 JSON 資料 → 多空分析
│   ├── utils_podcast_tw.py             # ✨ 台股 podcast 公用工具（你剛建立的）
│   ├── synthesize_audio.py             # 語音合成（edge-tts）
│   ├── upload_to_b2.py                 # 上傳音檔至 Backblaze B2
│   ├── generate_rss.py                 # 產生獨立 RSS（如 podcast_tw.xml）
│   ├── merge_rss_feeds.py              # 合併 tw/us RSS 成主 podcast.xml
│   └── fetch_ai_topic.py               # 擷取 AI 工具與新創產業內容（選填）
│
├── tw_market_data.txt                  # 台股 Grok 用 prompt（第一階段）
├── ai_topic.txt                        # AI 主題內容（每日更新）
├── bullish_signal_tw.txt              # 多空分析結果（每日更新）
│
├── requirements.txt                   # Python 套件清單
├── README.md
└── .env.template                      # 範例環境變數

專案整體目錄架構（優化版）
daily-podcast-stk/
├── .github/
│   └── workflows/
│       ├── podcast_workflow.yml       # 主工作流管道
│       ├── data_collection.yml        # 獨立資料收集排程
│       ├── strategy_management.yml    # 獨立策略管理排程
│       ├── market_analysis.yml        # 獨立市場分析排程
│       ├── script_editing.yml         # 獨立文字編輯排程
│       ├── podcast_production.yml     # 獨立播報排程
│       ├── upload_management.yml      # 獨立上傳排程
│       └── feed_publishing.yml        # 獨立推播排程
├── scripts/
│   ├── data_collector.py              # 資料收集員腳本
│   ├── strategy_manager.py            # 策略管理師腳本
│   ├── market_analyst.py              # 市場分析師腳本
│   ├── script_editor.py               # 文字編輯師腳本
│   ├── podcast_producer.py            # 播報員腳本
│   ├── upload_manager.py              # 雲端上傳員腳本
│   └── feed_publisher.py              # 推播員腳本
├── data/
│   ├── daily_*.csv                    # 日線數據
│   ├── hourly_*.csv                   # 小時線數據
│   ├── strategy_best_*.json           # 最佳策略結果
│   ├── market_analysis_*.json         # 市場分析結果
│   └── backup/                        # 數據備份（可擴充）
├── docs/
│   ├── podcast/
│   │   ├── YYYYMMDD_tw/               # 台股播報
│   │   │   ├── script.txt
│   │   │   ├── audio.mp3
│   │   │   └── archive_audio_url.txt
│   │   └── YYYYMMDD_us/               # 美股播報
│   │       ├── script.txt
│   │       ├── audio.mp3
│   │       └── archive_audio_url.txt
│   └── rss/
│       ├── podcast_tw.xml             # 台股 RSS
│       ├── podcast_us.xml             # 美股 RSS
│       └── podcast.xml                # 總 RSS
├── logs/
│   ├── data_collector.log             # 資料收集日誌
│   ├── strategy_manager.log           # 策略管理日誌
│   ├── market_analyst.log             # 市場分析日誌
│   ├── script_editor.log              # 文字編輯日誌
│   ├── podcast_producer.log           # 播報日誌
│   ├── upload_manager.log             # 上傳日誌
│   └── feed_publisher.log             # 推播日誌
├── config.json                        # 全域配置（符號、時間範圍）
├── strategies.json                    # 策略配置（僅供策略管理師）
├── README.md                          # 專案說明
└── .gitignore                         # 忽略文件
