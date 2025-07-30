# scripts/weekly_summary.py
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import pytz

class WeeklySummaryGenerator:
    def __init__(self):
        self.tz = pytz.timezone('Asia/Taipei')
        self.data_dir = 'data'
    
    def generate_weekly_summary(self):
        """生成週度摘要"""
        now = datetime.now(self.tz)
        
        # 計算本週範圍 (週一到週五)
        weekday = now.weekday()  # 0=週一, 6=週日
        
        # 找到本週週一
        monday = now - timedelta(days=weekday)
        # 找到本週週五
        friday = monday + timedelta(days=4)
        
        print(f"📅 生成週度摘要: {monday.strftime('%Y-%m-%d')} ~ {friday.strftime('%Y-%m-%d')}")
        
        summary_data = {
            'week_start': monday.strftime('%Y-%m-%d'),
            'week_end': friday.strftime('%Y-%m-%d'),
            'generated_time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'taiex_summary': self.analyze_taiex_week(monday, friday),
            'institutional_summary': self.analyze_institutional_week(monday, friday),
            'futures_summary': self.analyze_futures_week(monday, friday),
            'market_summary': {}
        }
        
        # 生成市場總結
        self.generate_market_summary(summary_data)
        
        # 儲存週度摘要
        self.save_weekly_summary(summary_data)
        
        # 顯示摘要
        self.display_weekly_summary(summary_data)
        
        return summary_data
    
    def get_week_data(self, file_path, start_date, end_date):
        """獲取週內資料"""
        if not os.path.exists(file_path):
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(file_path)
            df['日期'] = pd.to_datetime(df['日期'])
            
            week_data = df[
                (df['日期'] >= start_date.strftime('%Y-%m-%d')) & 
                (df['日期'] <= end_date.strftime('%Y-%m-%d'))
            ]
            
            return week_data.sort_values('日期')
            
        except Exception as e:
            print(f"❌ 讀取 {file_path} 錯誤: {e}")
            return pd.DataFrame()
    
    def analyze_taiex_week(self, start_date, end_date):
        """分析週內加權指數表現"""
        df = self.get_week_data('data/taiex_summary.csv', start_date, end_date)
        
        if df.empty:
            return None
        
        first_day = df.iloc[0]
        last_day = df.iloc[-1]
        
        weekly_change = last_day['指數點位'] - first_day['指數點位']
        weekly_change_pct = (weekly_change / first_day['指數點位']) * 100
        
        return {
            'trading_days': len(df),
            'week_start_index': first_day['指數點位'],
            'week_end_index': last_day['指數點位'],
            'weekly_change': weekly_change,
            'weekly_change_percent': weekly_change_pct,
            'highest_index': df['指數點位'].max(),
            'lowest_index': df['指數點位'].min(),
            'total_volume': df['成交金額(億元)'].sum(),
            'avg_daily_volume': df['成交金額(億元)'].mean(),
            'up_days': len(df[df['漲跌點數'] > 0]),
            'down_days': len(df[df['漲跌點數'] < 0]),
            'flat_days': len(df[df['漲跌點數'] == 0])
        }
    
    def analyze_institutional_week(self, start_date, end_date):
        """分析週內三大法人動向"""
        df = self.get_week_data('data/institutional_summary.csv', start_date, end_date)
        
        if df.empty:
            return None
        
        investors = ['外資及陸資', '投信', '自營商', '三大法人合計']
        summary = {}
        
        for investor in investors:
            col_name = f'{investor}_買賣超_億元'
            if col_name in df.columns:
                total_net = df[col_name].sum()
                buy_days = len(df[df[col_name] > 0])
                sell_days = len(df[df[col_name] < 0])
                avg_daily = df[col_name].mean()
                
                summary[investor] = {
                    'total_net_buy': total_net,
                    'buy_days': buy_days,
                    'sell_days': sell_days,
                    'avg_daily': avg_daily,
                    'direction': '淨買超' if total_net > 0 else '淨賣超' if total_net < 0 else '持平'
                }
        
        return summary
    
    def analyze_futures_week(self, start_date, end_date):
        """分析週內期貨表現"""
        df = self.get_week_data('data/futures_summary.csv', start_date, end_date)
        
        if df.empty:
            return None
        
        first_day = df.iloc[0]
        last_day = df.iloc[-1]
        
        weekly_change = last_day['收盤價'] - first_day['收盤價']
        weekly_change_pct = (weekly_change / first_day['收盤價']) * 100 if first_day['收盤價'] != 0 else 0
        
        return {
            'trading_days': len(df),
            'week_start_close': first_day['收盤價'],
            'week_end_close': last_day['收盤價'],
            'weekly_change': weekly_change,
            'weekly_change_percent': weekly_change_pct,
            'highest_close': df['收盤價'].max(),
            'lowest_close': df['收盤價'].min(),
            'total_volume': df['成交量'].sum(),
            'avg_daily_volume': df['成交量'].mean(),
            'avg_open_interest': df['未平倉量'].mean(),
            'up_days': len(df[df['漲跌'] > 0]),
            'down_days': len(df[df['漲跌'] < 0])
        }
    
    def generate_market_summary(self, summary_data):
        """生成市場週度總結"""
        market_summary = {
            'overall_sentiment': '中性',
            'key_highlights': [],
            'risk_factors': [],
            'opportunities': []
        }
        
        # 分析指數表現
        if summary_data['taiex_summary']:
            taiex = summary_data['taiex_summary']
            if taiex['weekly_change_percent'] > 2:
                market_summary['key_highlights'].append(f"加權指數週漲 {taiex['weekly_change_percent']:.2f}%")
                market_summary['overall_sentiment'] = '樂觀'
            elif taiex['weekly_change_percent'] < -2:
                market_summary['key_highlights'].append(f"加權指數週跌 {abs(taiex['weekly_change_percent']):.2f}%")
                market_summary['risk_factors'].append("指數弱勢")
                market_summary['overall_sentiment'] = '謹慎'
        
        # 分析法人動向
        if summary_data['institutional_summary']:
            institutional = summary_data['institutional_summary']
            
            if '三大法人合計' in institutional:
                total_net = institutional['三大法人合計']['total_net_buy']
                if total_net > 100:
                    market_summary['key_highlights'].append(f"三大法人週淨買超 {total_net:.0f} 億元")
                    market_summary['opportunities'].append("法人資金持續流入")
                elif total_net < -100:
                    market_summary['risk_factors'].append(f"三大法人週淨賣超 {abs(total_net):.0f} 億元")
            
            if '外資及陸資' in institutional:
                foreign_net = institutional['外資及陸資']['total_net_buy']
                if foreign_net > 50:
                    market_summary['opportunities'].append("外資持續買超")
                elif foreign_net < -50:
                    market_summary['risk_factors'].append("外資持續賣超")
        
        # 分析期貨表現
        if summary_data['futures_summary']:
            futures = summary_data['futures_summary']
            if futures['avg_daily_volume'] > 100000:
                market_summary['key_highlights'].append("期貨成交量活絡")
        
        # 綜合判斷情緒
        risk_count = len(market_summary['risk_factors'])
        opportunity_count = len(market_summary['opportunities'])
        
        if opportunity_count > risk_count:
            market_summary['overall_sentiment'] = '樂觀'
        elif risk_count > opportunity_count:
            market_summary['overall_sentiment'] = '謹慎'
        
        summary_data['market_summary'] = market_summary
    
    def save_weekly_summary(self, summary_data):
        """儲存週度摘要"""
        # 儲存詳細JSON
        week_str = f"{summary_data['week_start'].replace('-', '')}_{summary_data['week_end'].replace('-', '')}"
        json_file = f"{self.data_dir}/weekly_summary_{week_str}.json"
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 週度摘要已儲存: {json_file}")
    
    def display_weekly_summary(self, summary_data):
        """顯示週度摘要"""
        print(f"\n📊 週度市場摘要 ({summary_data['week_start']} ~ {summary_data['week_end']})")
        print("=" * 70)
        
        # 加權指數週表現
        if summary_data['taiex_summary']:
            taiex = summary_data['taiex_summary']
            print(f"📈 台灣加權指數週表現:")
            print(f"   週初: {taiex['week_start_index']:,.2f}")
            print(f"   週末: {taiex['week_end_index']:,.2f}")
            print(f"   週漲跌: {taiex['weekly_change']:+.2f} ({taiex['weekly_change_percent']:+.2f}%)")
            print(f"   週高低: {taiex['highest_index']:,.2f} / {taiex['lowest_index']:,.2f}")
            print(f"   成交日: {taiex['up_days']}漲 {taiex['down_days']}跌 {taiex['flat_days']}平")
            print(f"   週成交額: {taiex['total_volume']:,.0f} 億元")
        
        # 期貨週表現
        if summary_data['futures_summary']:
            futures = summary_data['futures_summary']
            print(f"\n📊 台指期貨週表現:")
            print(f"   週初: {futures['week_start_close']:,.0f}")
            print(f"   週末: {futures['week_end_close']:,.0f}")
            print(f"   週漲跌: {futures['weekly_change']:+.0f} ({futures['weekly_change_percent']:+.2f}%)")
            print(f"   週成交量: {futures['total_volume']:,} 口")
        
        # 三大法人週動向
        if summary_data['institutional_summary']:
            print(f"\n💰 三大法人週買賣超:")
            institutional = summary_data['institutional_summary']
            
            for investor, data in institutional.items():
                if investor != '三大法人合計':
                    print(f"   {investor}: {data['direction']} {abs(data['total_net_buy']):.0f} 億元 ({data['buy_days']}買 {data['sell_days']}賣)")
            
            if '三大法人合計' in institutional:
                total = institutional['三大法人合計']
                print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print(f"   三大法人合計: {total['direction']} {abs(total['total_net_buy']):.0f} 億元")
        
        # 市場總結
        if summary_data['market_summary']:
            market = summary_data['market_summary']
            print(f"\n🎯 市場週度總結:")
            print(f"   整體情緒: {market['overall_sentiment']}")
            
            if market['key_highlights']:
                print(f"   重點表現: {'; '.join(market['key_highlights'])}")
            
            if market['opportunities']:
                print(f"   正面因素: {'; '.join(market['opportunities'])}")
            
            if market['risk_factors']:
                print(f"   風險因素: {'; '.join(market['risk_factors'])}")
        
        print(f"\n⏰ 摘要生成時間: {summary_data['generated_time']}")

def main():
    print("📅 台股週度摘要生成器啟動")
    print("=" * 50)
    
    generator = WeeklySummaryGenerator()
    
    try:
        # 生成週度摘要
        summary = generator.generate_weekly_summary()
        
        if summary:
            print("\n✅ 週度摘要生成完成")
        else:
            print("\n⚠️  無法生成週度摘要")
            
    except Exception as e:
        print(f"\n❌ 週度摘要生成錯誤: {e}")

if __name__ == "__main__":
    main()
