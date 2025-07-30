# scripts/institutional_investors_scraper.py
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os
import sys

class InstitutionalInvestorsScraper:
    def __init__(self):
        # 三大法人買賣超統計API
        self.institutional_url = "https://www.twse.com.tw/fund/BFI82U"
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
    
    def get_institutional_data(self, date_str):
        """
        獲取指定日期的三大法人買賣超資料
        date_str: 格式為 'YYYYMMDD'
        """
        params = {
            'dayDate': date_str,
            'type': 'day',
            'response': 'json'
        }
        
        try:
            response = requests.get(self.institutional_url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('stat') != 'OK':
                print(f"❌ API回應錯誤 ({date_str}): {data.get('stat', 'Unknown error')}")
                return None
                
            return data
            
        except Exception as e:
            print(f"❌ 請求錯誤 ({date_str}): {e}")
            return None
    
    def parse_institutional_data(self, raw_data, date_str):
        """解析三大法人買賣超資料"""
        if not raw_data or 'data' not in raw_data or not raw_data['data']:
            return None
        
        try:
            # 三大法人資料通常在前幾筆
            data_rows = raw_data['data']
            
            # 找到各法人的資料
            institutional_data = {}
            
            for row in data_rows:
                investor_type = row[0].strip()  # 投資人類型
                
                if '外資' in investor_type or '外陸資' in investor_type:
                    key = '外資及陸資'
                elif '投信' in investor_type:
                    key = '投信'
                elif '自營商' in investor_type:
                    key = '自營商'
                elif '三大法人合計' in investor_type or '合計' in investor_type:
                    key = '三大法人合計'
                else:
                    continue
                
                # 解析買賣超金額 (通常在第2欄，單位千元)
                net_buy_sell = float(row[1].replace(',', '')) if row[1].replace(',', '').replace('-', '').isdigit() else 0
                
                institutional_data[key] = {
                    '買賣超(千元)': net_buy_sell,
                    '買賣超(億元)': round(net_buy_sell / 100000, 2)  # 轉換為億元
                }
            
            # 如果沒有合計資料，自行計算
            if '三大法人合計' not in institutional_data and len(institutional_data) >= 3:
                total_net = sum([data['買賣超(千元)'] for data in institutional_data.values()])
                institutional_data['三大法人合計'] = {
                    '買賣超(千元)': total_net,
                    '買賣超(億元)': round(total_net / 100000, 2)
                }
            
            result = {
                '日期': datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d'),
                '抓取時間': datetime.now(self.tz).strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 加入各法人資料
            for investor, data in institutional_data.items():
                result[f'{investor}_買賣超_千元'] = data['買賣超(千元)']
                result[f'{investor}_買賣超_億元'] = data['買賣超(億元)']
            
            return result
            
        except Exception as e:
            print(f"❌ 資料解析錯誤 ({date_str}): {e}")
            print(f"原始資料: {raw_data}")
            return None
    
    def scrape_today(self):
        """抓取今日三大法人資料"""
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
        print(f"💰 開始抓取 {now.strftime('%Y-%m-%d')} 的三大法人買賣超資料...")
        
        # 獲取資料
        raw_data = self.get_institutional_data(date_str)
        if not raw_data:
            print("❌ 無法獲取原始資料")
            return False
        
        parsed_data = self.parse_institutional_data(raw_data, date_str)
        if not parsed_data:
            print("❌ 資料解析失敗")
            return False
        
        # 顯示抓取到的資料
        print(f"✅ 成功抓取三大法人資料:")
        
        # 顯示各法人買賣超
        for key, value in parsed_data.items():
            if '買賣超_億元' in key and '合計' not in key:
                investor_name = key.replace('_買賣超_億元', '')
                amount = value
                direction = "買超" if amount > 0 else "賣超" if amount < 0 else "平盤"
                print(f"   📊 {investor_name}: {direction} {abs(amount):.2f} 億元")
        
        # 顯示合計
        total_key = '三大法人合計_買賣超_億元'
        if total_key in parsed_data:
            total_amount = parsed_data[total_key]
            total_direction = "買超" if total_amount > 0 else "賣超" if total_amount < 0 else "平盤"
            print(f"   🎯 三大法人合計: {total_direction} {abs(total_amount):.2f} 億元")
        
        # 儲存資料
        self.save_data(parsed_data)
        return True
    
    def save_data(self, data):
        """儲存資料到檔案"""
        # 確保 data 目錄存在
        os.makedirs('data', exist_ok=True)
        
        # 儲存到每日檔案
        daily_file = f"data/institutional_{data['日期'].replace('-', '')}.json"
        with open(daily_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 更新或創建匯總檔案
        summary_file = "data/institutional_summary.csv"
        
        if os.path.exists(summary_file):
            # 讀取現有資料
            df = pd.read_csv(summary_file)
            # 檢查是否已有今日資料
            if data['日期'] in df['日期'].values:
                # 更新現有資料
                df = df[df['日期'] != data['日期']]  # 先移除舊資料
                new_row = pd.DataFrame([data])
                df = pd.concat([df, new_row], ignore_index=True)
                print(f"📝 更新現有資料: {data['日期']}")
            else:
                # 新增資料
                new_row = pd.DataFrame([data])
                df = pd.concat([df, new_row], ignore_index=True)
                print(f"➕ 新增資料: {data['日期']}")
        else:
            # 創建新檔案
            df = pd.DataFrame([data])
            print(f"🆕 創建新的三大法人匯總檔案")
        
        # 按日期排序並儲存
        df = df.sort_values('日期')
        df.to_csv(summary_file, index=False, encoding='utf-8-sig')
        
        # 保留最近100筆記錄
        if len(df) > 100:
            df = df.tail(100)
            df.to_csv(summary_file, index=False, encoding='utf-8-sig')
            print(f"🗑️  保留最近100筆記錄")
        
        print(f"💾 三大法人資料已儲存:")
        print(f"   📄 每日檔案: {daily_file}")
        print(f"   📊 匯總檔案: {summary_file}")
    
    def get_range_data(self, start_date, end_date):
        """
        獲取日期範圍內的三大法人資料
        start_date: 開始日期 'YYYY-MM-DD'
        end_date: 結束日期 'YYYY-MM-DD'
        """
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        all_data = []
        current_dt = start_dt
        
        print(f"開始抓取 {start_date} 到 {end_date} 的三大法人買賣超資料...")
        
        while current_dt <= end_dt:
            # 只處理交易日
            if self.is_trading_day(current_dt):
                date_str = current_dt.strftime('%Y%m%d')
                print(f"正在獲取 {current_dt.strftime('%Y-%m-%d')} 的資料...")
                
                raw_data = self.get_institutional_data(date_str)
                if raw_data:
                    parsed_data = self.parse_institutional_data(raw_data, date_str)
                    if parsed_data:
                        all_data.append(parsed_data)
                        print(f"  ✓ 成功獲取資料")
                    else:
                        print(f"  ✗ 資料解析失敗")
                else:
                    print(f"  ✗ 無法獲取資料")
                
                # 避免過於頻繁的請求
                import time
                time.sleep(3)
            else:
                reason = "週末" if current_dt.weekday() >= 5 else "假日"
                print(f"跳過 {current_dt.strftime('%Y-%m-%d')} ({reason})")
            
            current_dt += timedelta(days=1)
        
        return pd.DataFrame(all_data) if all_data else pd.DataFrame()
    
    def generate_report(self):
        """生成三大法人買賣超報告"""
        summary_file = "data/institutional_summary.csv"
        
        if not os.path.exists(summary_file):
            print("❌ 找不到三大法人匯總檔案")
            return
        
        df = pd.read_csv(summary_file)
        
        if df.empty:
            print("❌ 三大法人匯總檔案為空")
            return
        
        # 最新資料
        latest = df.iloc[-1]
        print(f"\n📋 最新三大法人買賣超 ({latest['日期']}):")
        
        # 顯示各法人最新買賣超
        investor_types = ['外資及陸資', '投信', '自營商', '三大法人合計']
        for investor in investor_types:
            col_name = f'{investor}_買賣超_億元'
            if col_name in latest:
                amount = latest[col_name]
                direction = "買超" if amount > 0 else "賣超" if amount < 0 else "平盤"
                print(f"   {investor}: {direction} {abs(amount):.2f} 億元")
        
        # 近期統計 (最近20筆)
        recent = df.tail(20)
        print(f"\n📊 近20個交易日統計:")
        
        for investor in investor_types:
            col_name = f'{investor}_買賣超_億元'
            if col_name in recent.columns:
                total_net = recent[col_name].sum()
                buy_days = len(recent[recent[col_name] > 0])
                sell_days = len(recent[recent[col_name] < 0])
                avg_amount = recent[col_name].mean()
                
                direction = "淨買超" if total_net > 0 else "淨賣超" if total_net < 0 else "持平"
                print(f"   {investor}:")
                print(f"     {direction}: {abs(total_net):.2f} 億元")
                print(f"     買超天數: {buy_days} 天, 賣超天數: {sell_days} 天")
                print(f"     平均每日: {avg_amount:+.2f} 億元")

def main():
    print("🚀 台股三大法人買賣超自動抓取程式啟動")
    print("=" * 60)
    
    scraper = InstitutionalInvestorsScraper()
    
    try:
        # 抓取今日資料
        success = scraper.scrape_today()
        
        if success:
            # 生成報告
            scraper.generate_report()
            print("\n✅ 三大法人程式執行完成")
            sys.exit(0)
        else:
            print("\n⚠️  今日無需抓取三大法人資料")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n❌ 三大法人程式執行錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()