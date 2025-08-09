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