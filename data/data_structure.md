# 數據結構說明

## 📁 目錄結構

```
data/
├── market/           # 市場數據（簡化結構）
│   ├── daily_TWII.csv          # 台股大盤日線
│   ├── daily_0050_TW.csv       # ETF 日線
│   ├── daily_2330_TW.csv       # 台積電日線
│   ├── daily_AAPL.csv          # 蘋果股票日線
│   ├── daily_BTC_USD.csv       # 比特幣日線
│   ├── hourly_TWII.csv         # 台股大盤小時線
│   ├── hourly_2330_TW.csv      # 台積電小時線
│   └── ...
├── news/YYYY-MM-DD/  # 新聞數據（按日期分組）
│   ├── taiwan_news.json        # 台股新聞
│   └── us_news.json            # 美股新聞
└── collection_report.json      # 數據收集報告
```

## 📊 市場數據格式

### CSV 檔案結構
每個 CSV 檔案包含以下欄位：

| 欄位 | 說明 | 範例 |
|------|------|------|
| Datetime | 時間戳記 | 2024-08-24 09:00:00+08:00 |
| Symbol | 股票代號 | 2330.TW |
| Open | 開盤價 | 985.00 |
| High | 最高價 | 990.00 |
| Low | 最低價 | 980.00 |
| Close | 收盤價 | 987.00 |
| Volume | 成交量 | 12345678 |
| Updated | 更新時間 | 2024-08-24T17:30:00+08:00 |

### 檔案命名規則

- **日線數據**: `daily_{clean_symbol}.csv`
- **小時線數據**: `hourly_{clean_symbol}.csv`

符號清理規則：
- `^TWII` → `TWII`
- `2330.TW` → `2330_TW`  
- `BTC-USD` → `BTC_USD`
- `GC=F` → `GC_F`

## 📰 新聞數據格式

### JSON 檔案結構
```json
[
  {
    "title": "新聞標題",
    "link": "https://example.com/news/123",
    "published": "Sat, 24 Aug 2024 10:30:00 +0800",
    "summary": "新聞摘要內容...",
    "source": "Yahoo Finance",
    "collected_at": "2024-08-24T17:30:00+08:00"
  }
]
```

## 🔄 數據更新機制

### GitHub Actions 自動執行
- **頻率**: 每4小時執行一次
- **UTC 時間**: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
- **台北時間**: 08:00, 12:00, 16:00, 20:00, 00:00, 04:00

### 數據保留政策
- **日線數據**: 保留最近 300 天
- **小時線數據**: 保留最近 14 天  
- **新聞數據**: 保留最近 30 天

## 📈 使用範例

### 1. 基本數據讀取

```python
from data_loader import get_stock_data, load_taiwan_stocks

# 讀取單一股票數據
tsmc_data = get_stock_data("2330.TW", "daily", days=30)

# 讀取台股市場數據
taiwan_stocks = load_taiwan_stocks("daily", days=90)
```

### 2. 技術指標計算

```python
from data_loader import get_stock_data

# 讀取數據並計算技術指標
data = get_stock_data("2330.TW", "daily", days=100, with_indicators=True)

# 數據現在包含 SMA, RSI, MACD, 布林通道等指標
print(data[['Close', 'SMA_20', 'RSI', 'MACD']].tail())
```

### 3. 最新價格查詢

```python
from data_loader import get_latest_prices

# 獲取台股最新價格
prices = get_latest_prices(market="taiwan")

for symbol, info in prices.items():
    print(f"{symbol}: {info['price']:.2f} ({info['change_pct']:+.2f}%)")
```

### 4. 新聞數據讀取

```python
from data_loader import get_market_news

# 獲取台股最近一週新聞
taiwan_news = get_market_news("taiwan", days=7)

for news in taiwan_news[:5]:  # 顯示前5則
    print(f"{news['title']} - {news['source']}")
```

## 🛠️ 策略開發

### 數據載入器
使用 `MarketDataLoader` 類別來載入和處理數據：

```python
from data_loader import MarketDataLoader

loader = MarketDataLoader()

# 獲取可用的股票代號
symbols = loader.get_available_symbols("daily")

# 載入多個股票數據
data = loader.load_multiple_symbols(["2330.TW", "^TWII"], "daily")

# 計算技術指標
for symbol, df in data.items():
    df_with_indicators = loader.calculate_technical_indicators(df)
```

### 策略範例
```python
class SimpleStrategy:
    def __init__(self):
        self.loader = MarketDataLoader()
    
    def analyze(self, symbol: str):
        # 載入數據
        data = self.loader.load_symbol_data(symbol, "daily", days=100)
        
        # 計算指標
        data = self.loader.calculate_technical_indicators(data)
        
        # 產生信號
        latest = data.iloc[-1]
        signal = "BUY" if latest['RSI'] < 30 else "SELL" if latest['RSI'] > 70 else "HOLD"
        
        return {
            'symbol': symbol,
            'signal': signal,
            'price': latest['Close'],
            'rsi': latest['RSI']
        }
```

## 🔍 數據狀態檢查

使用內建的狀態檢查工具：

```bash
# 檢查數據狀態
python scripts/check_data_status.py

# 檢查配置載入
python scripts/test_config.py

# 運行數據收集（測試模式）
python scripts/data_collector.py --test --market taiwan
```

## 📝 注意事項

1. **檔案格式**: 所有 CSV 檔案使用 UTF-8 編碼
2. **時間格式**: 統一使用 ISO 8601 格式，包含時區信息
3. **數據完整性**: 每次更新會自動合併新舊數據並去重
4. **錯誤處理**: 數據收集過程中的錯誤會記錄在日誌中
5. **版本控制**: 所有數據變更會自動提交到 GitHub

## 🚀 部署和維護

### GitHub Actions 設定
確保倉庫有以下檔案：
- `.github/workflows/data_collection.yml`
- `requirements.txt`
- `config/base_config.json`
- `config/strategies.json`

### 手動觸發
在 GitHub Actions 頁面可以手動觸發數據收集：
1. 選擇市場範圍（台股/美股/加密貨幣/全部）
2. 選擇是否清理舊數據
3. 執行工作流程

### 監控和警報
- 檢查 GitHub Actions 執行狀態
- 查看數據收集報告 (`data/collection_report.json`)
- 監控檔案大小和更新時間
