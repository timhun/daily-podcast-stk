# scripts/taiex_scraper.py
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os
import sys

class TAIEXScraperForGitHub:
    def __init__(self):
        self.index_url = "https://www.twse.com.tw/exchangeReport/FMTQIK"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 設定台灣時區
        self.tz = pytz.timezone('Asia/Taipei')
        
        # 台灣證交所假日列表 (2024-2025年)
        self.holidays = {
            '2024': [
                '2024-01-01', '2024-02-08', '2024-02-09', '2024-02-10', 
                '2024-02-11', '2024-02-12', '2024-02-13', '2024-02-14',
                '2024-02-28', '2024-04-04', '2024-04-05', '2024-05-01',
                '2024-06-10', '2024-09-17', '2024-10-10'
            ],
            '2025': [
                '2025-01-01', '2025-01-27', '2025-01-28', '2025-01-29',
                '2025-01-30', '2025-01-31', '2025-02-28', '2025-04-04',
                '2025-05-01', '2025-05-31', '2025-10-06', '2025-10-10'
            ]
        }
    
    def is_trading_day(self, date):
        """判斷是否為交易日"""
        # 檢查週末
        if date.weekday() >= 5:
            return False
        
        # 檢查假日
        date_str = date.strftime('%Y-%m-%d')
        year = str(date.year)
        
        if year in self.holidays and date_str in self.holidays[year]:
            return False
        
        return True
    
    def get_taiex_data(self, date_str):
        """獲取指定日期的加權指數資料"""
        params = {
            'date': date_str,
            'response': 'json'
        }
        
        try:
            response = requests.get(self.index_url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('stat') != 'OK':
                print(f"❌ API回應錯誤 ({date_str}): {data.get('stat', 'Unknown error')}")
                return None
                
            return data
            
        except Exception as e:
            print(f"❌ 請求錯誤 ({date_str}): {e}")
            return None
    
    def parse_taiex_data(self, raw_data, date_str):
        """解析加權指數資料"""
        if not raw_data or 'data' not in raw_data or not raw_data['data']:
            return None
        
        try:
            taiex_data = raw_data['data'][0]
            
            return {
                '日期': datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d'),
                '指數點位': float(taiex_data[1].replace(',', '')),
                '漲跌點數': float(taiex_data[2].replace(',', '')),
                '漲跌幅(%)': float(taiex_data[3]),
                '成交金額(億元)': float(taiex_data[4].replace(',', '')),
                '抓取時間': datetime.now(self.tz).strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            print(f"❌ 資料解析錯誤 ({date_str}): {e}")
            return None
    
    def scrape_today(self):
        """抓取今日資料"""
        now = datetime.now(self.tz)
        print(f"🕒 當前台灣時間: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 檢查是否為交易日
        if not self.is_trading_day(now):
            reason = "週末" if now.weekday() >= 5 else "假日"
            print(f"⏭️  今日為{reason}，跳過抓取")
            return False
        
        # 檢查時間是否合理 (避免在開盤前抓取)
        if now.hour < 9:
            print("⏰ 開盤前，跳過抓取")
            return False
        
        date_str = now.strftime('%Y%m%d')
        print(f"📈 開始抓取 {now.strftime('%Y-%m-%d')} 的加權指數資料...")
        
        # 獲取資料
        raw_data = self.get_taiex_data(date_str)
        if not raw_data:
            print("❌ 無法獲取原始資料")
            return False
        
        parsed_data = self.parse_taiex_data(raw_data, date_str)
        if not parsed_data:
            print("❌ 資料解析失敗")
            return False
        
        # 顯示抓取到的資料
        print(f"✅ 成功抓取資料:")
        print(f"   📊 指數點位: {parsed_data['指數點位']:,.2f}")
        print(f"   📈 漲跌: {parsed_data['漲跌點數']:+.2f} ({parsed_data['漲跌幅(%)']:+.2f}%)")
        print(f"   💰 成交金額: {parsed_data['成交金額(億元)']:,.0f} 億元")
        
        # 儲存資料
        self.save_data(parsed_data)
        return True
    
    def save_data(self, data):
        """儲存資料到檔案"""
        # 確保 data 目錄存在
        os.makedirs('data', exist_ok=True)
        
        # 儲存到每日檔案
        daily_file = f"data/taiex_{data['日期'].replace('-', '')}.json"
        with open(daily_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 更新或創建匯總檔案
        summary_file = "data/taiex_summary.csv"
        
        if os.path.exists(summary_file):
            # 讀取現有資料
            df = pd.read_csv(summary_file)
            # 檢查是否已有今日資料
            if data['日期'] in df['日期'].values:
                # 更新現有資料
                df.loc[df['日期'] == data['日期']] = [
                    data['日期'], data['指數點位'], data['漲跌點數'], 
                    data['漲跌幅(%)'], data['成交金額(億元)'], data['抓取時間']
                ]
                print(f"📝 更新現有資料: {data['日期']}")
            else:
                # 新增資料
                new_row = pd.DataFrame([data])
                df = pd.concat([df, new_row], ignore_index=True)
                print(f"➕ 新增資料: {data['日期']}")
        else:
            # 創建新檔案
            df = pd.DataFrame([data])
            print(f"🆕 創建新的匯總檔案")
        
        # 按日期排序並儲存
        df = df.sort_values('日期')
        df.to_csv(summary_file, index=False, encoding='utf-8-sig')
        
        # 保留最近100筆記錄
        if len(df) > 100:
            df = df.tail(100)
            df.to_csv(summary_file, index=False, encoding='utf-8-sig')
            print(f"🗑️  保留最近100筆記錄")
        
        print(f"💾 資料已儲存:")
        print(f"   📄 每日檔案: {daily_file}")
        print(f"   📊 匯總檔案: {summary_file}")
    
    def generate_report(self):
        """生成簡單的報告"""
        summary_file = "data/taiex_summary.csv"
        
        if not os.path.exists(summary_file):
            print("❌ 找不到匯總檔案")
            return
        
        df = pd.read_csv(summary_file)
        
        if df.empty:
            print("❌ 匯總檔案為空")
            return
        
        # 最新資料
        latest = df.iloc[-1]
        print(f"\n📋 最新資料 ({latest['日期']}):")
        print(f"   指數: {latest['指數點位']:,.2f}")
        print(f"   漲跌: {latest['漲跌點數']:+.2f} ({latest['漲跌幅(%)']:+.2f}%)")
        
        # 近期統計 (最近20筆)
        recent = df.tail(20)
        print(f"\n📊 近20個交易日統計:")
        print(f"   最高點: {recent['指數點位'].max():,.2f}")
        print(f"   最低點: {recent['指數點位'].min():,.2f}")
        print(f"   平均成交額: {recent['成交金額(億元)'].mean():,.0f} 億元")
        print(f"   上漲天數: {len(recent[recent['漲跌點數'] > 0])} 天")
        print(f"   下跌天數: {len(recent[recent['漲跌點數'] < 0])} 天")

def main():
    print("🚀 台灣加權指數自動抓取程式啟動")
    print("=" * 50)
    
    scraper = TAIEXScraperForGitHub()
    
    try:
        # 抓取今日資料
        success = scraper.scrape_today()
        
        if success:
            # 生成報告
            scraper.generate_report()
            print("\n✅ 程式執行完成")
            sys.exit(0)
        else:
            print("\n⚠️  今日無需抓取資料")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n❌ 程式執行錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()