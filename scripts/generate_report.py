# scripts/generate_report.py
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import pytz

class TaiwanStockReportGenerator:
    def __init__(self):
        self.tz = pytz.timezone('Asia/Taipei')
        self.data_dir = 'data'
    
    def generate_daily_report(self):
        """生成每日綜合報告"""
        now = datetime.now(self.tz)
        today_str = now.strftime('%Y-%m-%d')
        
        print(f"📊 生成 {today_str} 的台股綜合報告")
        print("=" * 50)
        
        report_data = {
            'date': today_str,
            'generated_time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'taiex_data': self.get_taiex_data(today_str),
            'institutional_data': self.get_institutional_data(today_str),
            'futures_data': self.get_futures_data(today_str),
            'summary': {}
        }
        
        # 生成摘要
        self.generate_summary(report_data)
        
        # 儲存報告
        self.save_report(report_data)
        
        # 顯示報告
        self.display_report(report_data)
        
        return report_data
    
    def get_taiex_data(self, date_str):
        """獲取加權指數資料"""
        taiex_file = "data/taiex_summary.csv"
        
        if not os.path.exists(taiex_file):
            print("⚠️  找不到加權指數資料")
            return None
        
        try:
            df = pd.read_csv(taiex_file)
            today_data = df[df['日期'] == date_str]
            
            if not today_data.empty:
                return today_data.iloc[0].to_dict()
            else:
                print(f"⚠️  找不到 {date_str} 的加權指數資料")
                return None
                
        except Exception as e:
            print(f"❌ 讀取加權指數資料錯誤: {e}")
            return None
    
    def get_institutional_data(self, date_str):
        """獲取三大法人資料"""
        institutional_file = "data/institutional_summary.csv"
        
        if not os.path.exists(institutional_file):
            print("⚠️  找不到三大法人資料")
            return None
        
        try:
            df = pd.read_csv(institutional_file)
            today_data = df[df['日期'] == date_str]
            
            if not today_data.empty:
                return today_data.iloc[0].to_dict()
            else:
                print(f"⚠️  找不到 {date_str} 的三大法人資料")
                return None
                
        except Exception as e:
            print(f"❌ 讀取三大法人資料錯誤: {e}")
            return None
    
    def get_futures_data(self, date_str):
        """獲取台指期貨資料"""
        futures_file = "data/futures_summary.csv"
        
        if not os.path.exists(futures_file):
            print("⚠️  找不到期貨資料")
            return None
        
        try:
            df = pd.read_csv(futures_file)
            today_data = df[df['日期'] == date_str]
            
            if not today_data.empty:
                return today_data.iloc[0].to_dict()
            else:
                print(f"⚠️  找不到 {date_str} 的期貨資料")
                return None
                
        except Exception as e:
            print(f"❌ 讀取期貨資料錯誤: {e}")
            return None
    
    def generate_summary(self, report_data):
        """生成綜合摘要"""
        summary = {}
        
        # 加權指數摘要
        if report_data['taiex_data']:
            taiex = report_data['taiex_data']
            summary['taiex'] = {
                'index_value': taiex.get('指數點位', 0),
                'change': taiex.get('漲跌點數', 0),
                'change_percent': taiex.get('漲跌幅(%)', 0),
                'volume': taiex.get('成交金額(億元)', 0),
                'trend': '上漲' if taiex.get('漲跌點數', 0) > 0 else '下跌' if taiex.get('漲跌點數', 0) < 0 else '平盤'
            }
        
        # 三大法人摘要
        if report_data['institutional_data']:
            institutional = report_data['institutional_data']
            
            # 提取各法人資料
            investors = ['外資及陸資', '投信', '自營商', '三大法人合計']
            summary['institutional'] = {}
            
            for investor in investors:
                col_name = f'{investor}_買賣超_億元'
                if col_name in institutional:
                    amount = institutional[col_name]
                    summary['institutional'][investor] = {
                        'amount': amount,
                        'direction': '買超' if amount > 0 else '賣超' if amount < 0 else '平盤'
                    }
        
        # 期貨摘要
        if report_data['futures_data']:
            futures = report_data['futures_data']
            summary['futures'] = {
                'contract_code': futures.get('合約代號', ''),
                'contract_month': futures.get('合約月份', ''),
                'close_price': futures.get('收盤價', 0),
                'change': futures.get('漲跌', 0),
                'change_percent': futures.get('漲跌幅(%)', 0),
                'volume': futures.get('成交量', 0),
                'open_interest': futures.get('未平倉量', 0),
                'trend': '上漲' if futures.get('漲跌', 0) > 0 else '下跌' if futures.get('漲跌', 0) < 0 else '平盤'
            }
        
        # 市場情緒判斷
        summary['market_sentiment'] = self.analyze_market_sentiment(summary)
        
        report_data['summary'] = summary
    
    def analyze_market_sentiment(self, summary):
        """分析市場情緒"""
        sentiment_score = 0
        factors = []
        
        # 指數漲跌影響
        if 'taiex' in summary:
            change_percent = summary['taiex'].get('change_percent', 0)
            if change_percent > 1:
                sentiment_score += 2
                factors.append("指數大漲")
            elif change_percent > 0:
                sentiment_score += 1
                factors.append("指數上漲")
            elif change_percent < -1:
                sentiment_score -= 2
                factors.append("指數大跌")
            elif change_percent < 0:
                sentiment_score -= 1
                factors.append("指數下跌")
        
        # 三大法人影響
        if 'institutional' in summary:
            # 外資影響權重最大
            if '外資及陸資' in summary['institutional']:
                foreign_amount = summary['institutional']['外資及陸資'].get('amount', 0)
                if foreign_amount > 50:
                    sentiment_score += 2
                    factors.append("外資大買")
                elif foreign_amount > 0:
                    sentiment_score += 1
                    factors.append("外資買超")
                elif foreign_amount < -50:
                    sentiment_score -= 2
                    factors.append("外資大賣")
                elif foreign_amount < 0:
                    sentiment_score -= 1
                    factors.append("外資賣超")
            
            # 投信影響
            if '投信' in summary['institutional']:
                fund_amount = summary['institutional']['投信'].get('amount', 0)
                if fund_amount > 20:
                    sentiment_score += 1
                    factors.append("投信買超")
                elif fund_amount < -20:
                    sentiment_score -= 1
                    factors.append("投信賣超")
        
        # 判斷整體情緒
        if sentiment_score >= 3:
            sentiment = "非常樂觀"
        elif sentiment_score >= 1:
            sentiment = "樂觀"
        elif sentiment_score <= -3:
            sentiment = "非常悲觀"
        elif sentiment_score <= -1:
            sentiment = "悲觀"
        else:
            sentiment = "中性"
        
        return {
            'sentiment': sentiment,
            'score': sentiment_score,
            'factors': factors
        }
    
    def save_report(self, report_data):
        """儲存綜合報告"""
        # 儲存為JSON
        date_str = report_data['date'].replace('-', '')
        json_file = f"{self.data_dir}/daily_report_{date_str}.json"
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        # 更新報告匯總
        summary_file = f"{self.data_dir}/reports_summary.csv"
        
        # 建立簡化的報告資料用於CSV
        csv_data = {
            '日期': report_data['date'],
            '生成時間': report_data['generated_time']
        }
        
        # 加入加權指數資料
        if report_data['taiex_data']:
            csv_data.update({
                '指數點位': report_data['summary']['taiex']['index_value'],
                '指數漲跌點數': report_data['summary']['taiex']['change'],
                '指數漲跌幅(%)': report_data['summary']['taiex']['change_percent'],
                '成交金額(億元)': report_data['summary']['taiex']['volume']
            })
          # 加入三大法人資料
        if report_data['institutional_data']:
            for investor in ['外資及陸資', '投信', '自營商', '三大法人合計']:
                csv_data[f'{investor}_買賣超_億元'] = report_data['institutional_data'].get(f'{investor}_買賣超_億元', 0)
        
        # 加入期貨資料
        if report_data['futures_data']:
            csv_data.update({
                '期貨合約': report_data['futures_data'].get('合約代號', ''),
                '期貨收盤價': report_data['futures_data'].get('收盤價', 0),
                '期貨漲跌': report_data['futures_data'].get('漲跌', 0),
                '期貨漲跌幅(%)': report_data['futures_data'].get('漲跌幅(%)', 0),
                '期貨成交量': report_data['futures_data'].get('成交量', 0),
                '期貨未平倉': report_data['futures_data'].get('未平倉量', 0)
            })
        
        # 加入市場情緒
        csv_data['市場情緒'] = report_data['summary']['market_sentiment']['sentiment']
        csv_data['情緒分數'] = report_data['summary']['market_sentiment']['score']
        
        # 更新CSV匯總
        if os.path.exists(summary_file):
            df = pd.read_csv(summary_file)
            if report_data['date'] in df['日期'].values:
                df = df[df['日期'] != report_data['date']]
            new_row = pd.DataFrame([csv_data])
            df = pd.concat([df, new_row], ignore_index=True)
        else:
            df = pd.DataFrame([csv_data])
        
        df = df.sort_values('日期')
        df.to_csv(summary_file, index=False, encoding='utf-8-sig')
        
        print(f"💾 綜合報告已儲存:")
        print(f"   📄 詳細報告: {json_file}")
        print(f"   📊 報告匯總: {summary_file}")
    
    def display_report(self, report_data):
        """顯示綜合報告"""
        print(f"\n📊 {report_data['date']} 台股市場綜合報告")
        print("=" * 60)
        
        # 加權指數部分
        if report_data['taiex_data']:
            taiex = report_data['summary']['taiex']
            print(f"📈 台灣加權指數:")
            print(f"   點位: {taiex['index_value']:,.2f}")
            print(f"   漲跌: {taiex['change']:+.2f} ({taiex['change_percent']:+.2f}%) - {taiex['trend']}")
            print(f"   成交金額: {taiex['volume']:,.0f} 億元")
        
        # 期貨部分
        if report_data['futures_data']:
            futures = report_data['summary']['futures']
            print(f"\n📊 台指期貨 ({futures['contract_code']}):")
            print(f"   收盤價: {futures['close_price']:,.0f}")
            print(f"   漲跌: {futures['change']:+.0f} ({futures['change_percent']:+.2f}%) - {futures['trend']}")
            print(f"   成交量: {futures['volume']:,} 口")
            print(f"   未平倉: {futures['open_interest']:,} 口")
        
        # 三大法人部分
        if report_data['institutional_data']:
            print(f"\n💰 三大法人買賣超:")
            institutional = report_data['summary']['institutional']
            for investor, data in institutional.items():
                if investor != '三大法人合計':
                    print(f"   {investor}: {data['direction']} {abs(data['amount']):.2f} 億元")
            
            if '三大法人合計' in institutional:
                total = institutional['三大法人合計']
                print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print(f"   三大法人合計: {total['direction']} {abs(total['amount']):.2f} 億元")
        
        # 市場情緒分析
        if 'market_sentiment' in report_data['summary']:
            sentiment = report_data['summary']['market_sentiment']
            print(f"\n🎯 市場情緒分析:")
            print(f"   整體情緒: {sentiment['sentiment']} (分數: {sentiment['score']})")
            if sentiment['factors']:
                print(f"   主要因素: {', '.join(sentiment['factors'])}")
        
        print(f"\n⏰ 報告生成時間: {report_data['generated_time']}")

def main():
    print("📊 台股綜合報告生成器啟動")
    print("=" * 50)
    
    generator = TaiwanStockReportGenerator()
    
    try:
        # 生成今日報告
        report = generator.generate_daily_report()
        
        if report:
            print("\n✅ 綜合報告生成完成")
            sys.exit(0)
        else:
            print("\n⚠️  無法生成綜合報告")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ 報告生成錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
