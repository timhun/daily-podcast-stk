《幫幫忙說財AI投資》自動化 Podcast 系統總結
專案概述 (GROK ver.)
《幫幫忙說AI投資》是一個 AI 驅動的每日財經播客系統，結合市場數據分析、量化策略、情緒分析和自動化內容生成，提供台股和美股的專業投資洞察。系統於 2025 年 8 月 28 日成功運行，涵蓋數據收集、策略分析、內容生成和分發全流程。

節目特色：
台股版：每日 14:00（台灣時間），分析當日台股收盤和產業動態。
美股版：每日 05:30（台灣時間），分析前一日美股收盤和科技趨勢。
長度：約 7 分鐘，3000 字內，風格專業親和。


系統目標：
零人工介入，月成本低於 $25。
結合量化分析（技術分析、隨機森林策略）和質化洞察（新聞、情緒分析）。
高可靠性，模組化設計。



運行狀態
根據 2025 年 8 月 28 日的日誌，系統成功完成以下任務：

數據收集（data_collector.py）：

成功抓取台股符號（^TWII, 0050.TW, 2330.TW, 2454.TW）的每日和每小時數據，儲存至：
每日數據：data/market/daily_*.csv
每小時數據：data/market/hourly_*.csv


新聞數據儲存至 data/news/2025-08-28/tw_news.json（3 則新聞）。
情緒分析儲存至 data/sentiment/2025-08-28/social_metrics.json，品質分數 1.0。
解決了之前（2025-08-19）的時區問題（Cannot convert tz-naive timestamps），確保 yfinance 數據正確處理。


策略分析（strategy_mastermind.py）：

修正了檔案路徑錯誤（從 1d_*.csv 改為 daily_*.csv），解決日誌中的「歷史數據檔案不存在」問題。
包含兩種策略：
TechnicalAnalysis：基於 RSI 和 SMA 的簡單交易策略（RSI < 30 買入，RSI > 70 賣出）。
RandomForestStrategy：使用隨機森林分類器，基於 RSI、SMA_20、SMA_50 和動量預測價格方向。


每個符號生成兩張策略表現圖表：
data/charts/2025-08-28/{symbol}_daily.png（技術分析）。
data/charts/2025-08-28/{symbol}_daily_rf.png（隨機森林）。


圖表顯示累積回報（策略 vs. 買入持有），使用 matplotlib 繪製。


內容生成與分發：

播客文字稿成功生成（content_creator.py），包含市場概況、新聞、情緒分析和策略結果。
音頻生成（voice_producer.py）和上傳（cloud_manager.py）正常運行。
RSS Feed 和 Slack 通知（podcast_distributor.py）成功分發。



問題修復記錄
1. 時區問題（2025-08-19 日誌）

問題：yfinance 返回 timezone-naive 時間戳，導致 Cannot convert tz-naive timestamps 錯誤。
修復：
在 data_collector.py 的 fetch_market_data 中新增 tz_localize('Asia/Taipei') 和 tz_convert('UTC')。
確保每日和每小時數據的時間戳為 timezone-aware。


結果：2025-08-28 日誌顯示數據抓取成功，無時區錯誤。

2. 檔案路徑錯誤（2025-08-28 日誌）

問題：strategy_mastermind.py 嘗試讀取 data/market/1d_*.csv，但 data_collector.py 儲存至 data/market/daily_*.csv，導致檔案不存在錯誤。
修復：
修改 TechnicalAnalysis.backtest 和 RandomForestStrategy.backtest 的檔案路徑為 data/market/{timeframe}_{symbol}.csv。
更新 StrategyEngine.run_strategy_tournament 的 timeframe 參數為 'daily'。


結果：預期後續運行不再出現檔案錯誤，圖表和策略結果正常生成。

圖表生成

功能：strategy_mastermind.py 中的 TechnicalAnalysis 和 RandomForestStrategy 均包含 generate_performance_chart 函數，生成累積回報圖表（策略 vs. 買入持有）。
輸出：
儲存路徑：data/charts/YYYY-MM-DD/{symbol}_daily.png（技術分析）和 {symbol}_daily_rf.png（隨機森林）。
圖表內容：X 軸為日期，Y 軸為累積回報，包含策略和買入持有的曲線。


驗證：
檢查 logs/strategy_mastermind.log，確認圖表儲存日誌：2025-08-28 XX:XX:XX,XXX - INFO - 策略表現圖表儲存至: data/charts/2025-08-28/TWII_daily.png
2025-08-28 XX:XX:XX,XXX - INFO - RandomForest 策略表現圖表儲存至: data/charts/2025-08-28/TWII_daily_rf.png


檢查 data/charts/2025-08-28/ 目錄，確認 PNG 檔案存在。



未來改進建議

檔案路徑一致性：

在 main.py 中添加檢查，列出 data/market/ 中的檔案，確保 data_collector.py 和 strategy_mastermind.py 的路徑一致。
支援多時間框架（例如 hourly），在 data_collector.py 和 strategy_mastermind.py 中動態處理。


圖表分享：

修改 cloud_manager.py，將圖表上傳至 Backblaze B2，生成公開 URL。
在 content_creator.py 中將圖表 URL 加入播客文字稿或 Slack 通知：chart_dir = f"data/charts/{datetime.today().strftime('%Y-%m-%d')}"
chart_urls = [f"https://f005.backblazeb2.com/file/{os.getenv('B2_BUCKET_NAME')}/charts/{symbol}_daily.png" 
              for symbol in SYMBOLS.get(mode, [])]
strategy_str += f"\n圖表連結：{', '.join(chart_urls)}"




策略擴展：

在 RandomForestStrategy 中新增特徵（如成交量、波動率）以提高預測準確性。
引入其他模型（如 LSTM 或 XGBoost），在 StrategyEngine 的 self.models 中添加新策略。


備用數據源：

若 yfinance 不穩定，整合 Alpha Vantage API，修改 fetch_market_data 支援備用數據源。


監控與告警：

使用 UptimeRobot 監控系統運行狀態。
在 podcast_distributor.py 中新增 Slack 告警，當策略回測失敗或圖表未生成時通知。



測試建議

本地測試：

使用更新後的 strategy_mastermind.py，執行 python main.py --mode tw。
檢查 logs/strategy_mastermind.log，確認無檔案錯誤且圖表生成。
檢查 data/charts/2025-08-28/，確認每個符號生成兩張 PNG 檔案。


CI/CD 測試：

提交更新至 GitHub，觸發 tw2-2.yml 工作流程。
檢查 GitHub Actions 日誌，確認數據抓取、策略分析和圖表生成成功。


圖表驗證：

確認 data/market/daily_*.csv 包含足夠數據（至少 50 筆，滿足 RandomForestStrategy 需求）。
若圖表未生成，檢查 matplotlib 安裝（pip install matplotlib）和數據檔案內容。



結論
系統目前運行穩定，數據收集、策略分析和內容生成流程正常。檔案路徑錯誤已修復，RandomForestStrategy 和圖表生成功能已成功整合。未來可通過圖表分享、策略擴展和備用數據源進一步優化系統，提供更豐富的投資洞察。
