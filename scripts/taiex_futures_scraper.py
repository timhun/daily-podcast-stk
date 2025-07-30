# scripts/taiex_futures_scraper.py
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os
import sys
import re

class TAIEXFuturesScraper:
    def __init__(self):
        # 台灣期貨交易所API
        self.futures_url = "https://www.taifex.com.tw/cht/3/dlFutDataDown"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.taifex.com.tw/'
        }
        
        # 設定台灣時區
        self.tz = pytz.timezone('Asia/Taipei')
        
        # 台灣期交所假日列表 (與證交所相同)
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
        
        # 台指期貨合約代碼 (TX為台指期貨)
        self.futures_code = 'TX'
    
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
    
    def get_current_futures_contract(self, date):
        """
        取得當前的近月期貨合約
        台指期貨交割月份為3、6、9、12月第三個週三
        """
        year = date.year
        month = date.month
        
        # 決定近月合約月份
        delivery_months = [3, 6, 9, 12]
        
        # 找到當前月份後的下一個交割月份
        next_delivery_month = None
        for dm in delivery_months:
            if month <= dm:
                next_delivery_month = dm
                break
        
        # 如果當前月份大於12月的交割月，則用下一年的3月
        if next_delivery_month is None:
            next_delivery_month = 3
            year += 1
        
        # 檢查是否已過交割日
        if month == next_delivery_month:
            # 計算第三個週三
            third_wednesday = self.get_third_wednesday(year, month)
            if date >= third_wednesday:
                # 已過交割日，使用下一個交割月
                current_index = delivery_months.index(next_delivery_month)
                if current_index < 3:
                    next_delivery_month = delivery_months[current_index + 1]
                else:
                    next_delivery_month = 3
                    year += 1
        
        # 生成合約代碼：TX + 年份後兩碼 + 月份代碼
        year_code = str(year)[-2:]
        
        # 月份代碼對應
        month_codes = {3: '03', 6: '06', 9: '09', 12: '12'}
        month_code = month_codes[next_delivery_month]
        
        contract_code = f"{self.futures_code}{year_code}{month_code}"
        
        return contract_code, f"{year}/{next_delivery_month:02d}"
    
    def get_third_wednesday(self, year, month):
        """計算指定年月的第三個週三"""
        # 找到該月第一天
        first_day = datetime(year, month, 1)
        
        # 找到第一個週三
        days_until_wednesday = (2 - first_day.weekday()) % 7
        first_wednesday = first_day + timedelta(days=days_until_wednesday)
        
        # 第三個週三
        third_wednesday = first_wednesday + timedelta(weeks=2)
        
        return third_wednesday
    
    def get_futures_data(self, date_str):
        """
        獲取台指期貨資料
        date_str: 格式為 'YYYY/MM/DD'
        """
        params = {
            'down_type': '1',
            'commodity_id': 'TX',
            'queryStartDate': date_str,
            'queryEndDate': date_str
        }
        
        try:
            response = requests.get(self.futures_url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # 期交所回傳的是CSV格式
            content = response.text
            
            if '查無資料' in content or len(content.strip()) == 0:
                print(f"❌ 無期貨資料 ({date_str})")
                return None
            
            return content
            
        except Exception as e:
            print(f"❌ 期貨請求錯誤 ({date_str}): {e}")
            return None
    
    def parse_futures_data(self, raw_data, date_str):
        """解析台指期貨資料"""
        if not raw_data:
            return None
        
        try:
            # 分割行
            lines = raw_data.strip().split('\n')
            
            if len(lines) < 2:
                print(f"❌ 期貨資料格式錯誤 ({date_str})")
                return None
            
            # 找到標題行和資料行
            header_found = False
            data_lines = []
            
            for line in lines:
                if '交易日期' in line or '商品代號' in line:
                    header_found = True
                    continue
                
                if header_found and line.strip():
                    # 清理資料行
                    cleaned_line = line.strip().replace('"', '')
                    if cleaned_line:
                        data_lines.append(cleaned_line.split(','))
            
            if not data_lines:
                print(f"❌ 找不到期貨資料行 ({date_str})")
                return None
            
            # 獲取當前近月合約
            current_date = datetime.strptime(date_str, '%Y/%m/%d')
            target_contract, contract_month = self.get_current_futures_contract(current_date)
            
            # 尋找近月合約資料
            futures_data = None
            for data_row in data_lines:
                if len(data_row) >= 10:
                    # 期貨合約代號通常在第2欄或第3欄
                    contract_code = data_row[1] if len(data_row) > 1 else ""
                    
                    # 檢查是否為目標合約
                    if target_contract in contract_code or self.is_near_month_contract(contract_code, current_date):
                        futures_data = data_row
                        break
            
            if not futures_data:
                print(f"❌ 找不到近月台指期貨資料 ({date_str})")
                return None
            
            # 解析資料欄位
            try:
                result = {
                    '日期': current_date.strftime('%Y-%m-%d'),
                    '合約代號': futures_data[1] if len(futures_data) > 1 else '',
                    '合約月份': contract_month,
                    '開盤價': float(futures_data[3].replace(',', '')) if len(futures_data) > 3 and futures_data[3].replace(',', '').replace('.', '').isdigit() else 0,
                    '最高價': float(futures_data[4].replace(',', '')) if len(futures_data) > 4 and futures_data[4].replace(',', '').replace('.', '').isdigit() else 0,
                    '最低價': float(futures_data[5].replace(',', '')) if len(futures_data) > 5 and futures_data[5].replace(',', '').replace('.', '').isdigit() else 0,
                    '收盤價': float(futures_data[6].replace(',', '')) if len(futures_data) > 6 and futures_data[6].replace(',', '').replace('.', '').isdigit() else 0,
                    '漲跌': float(futures_data[7].replace(',', '')) if len(futures_data) > 7 and futures_data[7].replace(',', '').replace('.', '').replace('+', '').replace('-', '').isdigit() else 0,
                    '成交量': int(futures_data[8].replace(',', '')) if len(futures_data) > 8 and futures_data[8].replace(',', '').isdigit() else 0,
                    '未平倉量': int(futures_data[10].replace(',', '')) if len(futures_data) > 10 and futures_data[10].replace(',', '').isdigit() else 0,
                    '抓取時間': datetime.now(self.tz).strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # 計算漲跌幅
                if result['收盤價'] > 0 and result['漲跌'] != 0:
                    previous_close = result['收盤價'] - result['漲跌']
                    if previous_close != 0:
                        result['漲跌幅(%)'] = round((result['漲跌'] / previous_close) * 100, 2)
                    else:
                        result['漲跌幅(%)'] = 0
                else:
                    result['漲跌幅(%)'] = 0
                
                return result
                
            except (ValueError, IndexError) as e:
                print(f"❌ 期貨資料解析錯誤 ({date_str}): {e}")
                print(f"原始資料: {futures_data}")
                return None
            
        except Exception as e:
            print(f"❌ 期貨資料處理錯誤 ({date_str}): {e}")
            return None
    
    def is_near_month_contract(self, contract_code, current_date):
        """判斷是否為近月合約"""
        if not contract_code or len(contract_code) < 5:
            return False
        
        # 提取合約中的年月資訊
        match = re.search(r'TX(\d{2})(\d{2})', contract_code)
        if not match:
            return False
        
        contract_year = 2000 + int(match.group(1))
        contract_month = int(match.group(2))
        
        # 檢查是否為當前的近月合約
        target_contract, _ = self.get_current_futures_contract(current_date)
        
        return contract_code == target_contract
    
    def scrape_today(self):
        """抓取今日台指期貨資料"""
        now = datetime.now(self.tz)
        print(f"🕒 當前台灣時間: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 檢查是否為交易日
        if not self.is_trading_day(now):
            reason = "週末" if now.weekday() >= 5 else "假日"
            print(f"⏭️  今日為{reason}，跳過期貨抓取")
            return False
        
        # 檢查時間是否合理
        if now.hour < 8 or (now.hour == 8 and now.minute < 45):
            print("⏰ 期貨開盤前，跳過抓取")
            return False
        
        date_str = now.strftime('%Y/%m/%d')
        print(f"📈 開始抓取 {now.strftime('%Y-%m-%d')} 的台指期貨資料...")
        
        # 顯示目標合約
        target_contract, contract_month = self.get_current_futures_contract(now)
        print(f"🎯 目標合約: {target_contract} ({contract_month})")
        
        # 獲取資料
        raw_data = self.get_futures_data(date_str)
        if not raw_data:
            print("❌ 無法獲取期貨原始資料")
            return False
        
        parsed_data = self.parse_futures_data(raw_data, date_str)
        if not parsed_data:
            print("❌ 期貨資料解析失敗")
            return False
        
        # 顯示抓取到的資料
        print(f"✅ 成功抓取台指期貨資料:")
        print(f"   📊 合約: {parsed_data['合約代號']} ({parsed_data['合約月份']})")
        print(f"   💰 收盤價: {parsed_data['收盤價']:,.0f}")
        print(f"   📈 漲跌: {parsed_data['漲跌']:+.0f} ({parsed_data['漲跌幅(%)']:+.2f}%)")
        print(f"   📦 成交量: {parsed_data['成交量']:,} 口")
        print(f"   🏦 未平倉: {parsed_data['未平倉量']:,} 口")
        
        # 儲存資料
        self.save_data(parsed_data)
        return True
    
    def save_data(self, data):
        """儲存期貨資料到檔案"""
        # 確保 data 目錄存在
        os.makedirs('data', exist_ok=True)
        
        # 儲存到每日檔案
        daily_file = f"data/futures_{data['日期'].replace('-', '')}.json"
        with open(daily_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 更新或創建匯總檔案
        summary_file = "data/futures_summary.csv"
        
        if os.path.exists(summary_file):
            # 讀取現有資料
            df = pd.read_csv(summary_file)
            # 檢查是否已有今日資料
            if data['日期'] in df['日期'].values:
                # 更新現有資料
                df = df[df['日期'] != data['日期']]  # 先移除舊資料
                new_row = pd.DataFrame([data])
                df = pd.concat([df, new_row], ignore_index=True)
                print(f"📝 更新期貨現有資料: {data['日期']}")
            else:
                # 新增資料
                new_row = pd.DataFrame([data])
                df = pd.concat([df, new_row], ignore_index=True)
                print(f"➕ 新增期貨資料: {data['日期']}")
        else:
            # 創建新檔案
            df = pd.DataFrame([data])
            print(f"🆕 創建新的期貨匯總檔案")
        
        # 按日期排序並儲存
        df = df.sort_values('日期')
        df.to_csv(summary_file, index=False, encoding='utf-8-sig')
        
        # 保留最近100筆記錄
        if len(df) > 100:
            df = df.tail(100)
            df.to_csv(summary_file, index=False, encoding='utf-8-sig')
            print(f"🗑️  保留最近100筆期貨記錄")
        
        print(f"💾 期貨資料已儲存:")
        print(f"   📄 每日檔案: {daily_file}")
        print(f"   📊 匯總檔案: {summary_file}")
    
    def generate_report(self):
        """生成台指期貨報告"""
        summary_file = "data/futures_summary.csv"
        
        if not os.path.exists(summary_file):
            print("❌ 找不到期貨匯總檔案")
            return
        
        df = pd.read_csv(summary_file)
        
        if df.empty:
            print("❌ 期貨匯總檔案為空")
            return
        
        # 最新資料
        latest = df.iloc[-1]
        print(f"\n📋 最新台指期貨資料 ({latest['日期']}):")
        print(f"   合約: {latest['合約代號']} ({latest['合約月份']})")
        print(f"   收盤價: {latest['收盤價']:,.0f}")
        print(f"   漲跌: {latest['漲跌']:+.0f} ({latest['漲跌幅(%)']:+.2f}%)")
        print(f"   成交量: {latest['成交量']:,} 口")
        print(f"   未平倉: {latest['未平倉量']:,} 口")
        
        # 近期統計 (最近20筆)
        recent = df.tail(20)
        print(f"\n📊 近20個交易日期貨統計:")
        print(f"   最高收盤: {recent['收盤價'].max():,.0f}")
        print(f"   最低收盤: {recent['收盤價'].min():,.0f}")
        print(f"   平均成交量: {recent['成交量'].mean():,.0f} 口")
        print(f"   上漲天數: {len(recent[recent['漲跌'] > 0])} 天")
        print(f"   下跌天數: {len(recent[recent['漲跌'] < 0])} 天")
        print(f"   平均未平倉: {recent['未平倉量'].mean():,.0f} 口")

def main():
    print("🚀 台指期貨自動抓取程式啟動")
    print("=" * 50)
    
    scraper = TAIEXFuturesScraper()
    
    try:
        # 抓取今日資料
        success = scraper.scrape_today()
        
        if success:
            # 生成報告
            scraper.generate_report()
            print("\n✅ 期貨程式執行完成")
            sys.exit(0)
        else:
            print("\n⚠️  今日無需抓取期貨資料")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n❌ 期貨程式執行錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
