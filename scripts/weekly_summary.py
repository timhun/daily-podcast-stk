# scripts/weekly_summary.py
import json
import os
import logging
from datetime import datetime, timedelta
import pytz
import glob

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WeeklySummaryGenerator:
    def __init__(self):
        self.tz = pytz.timezone('Asia/Taipei')
        self.data_dir = 'data'
    
    def generate_weekly_summary(self):
        """生成週度摘要"""
        now = datetime.now(self.tz)
        
        # 計算本週範圍 (週一到週五)
        weekday = now.weekday()  # 0=週一, 6=週日
        monday = now - timedelta(days=weekday)
        friday = monday + timedelta(days=4)
        
        logger.info(f"📅 生成週度摘要: {monday.strftime('%Y-%m-%d')} ~ {friday.strftime('%Y-%m-%d')}")
        
        summary_data = {
            'week_start': monday.strftime('%Y-%m-%d'),
            'week_end': friday.strftime('%Y-%m-%d'),
            'generated_time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'taiex_summary': self.analyze_taiex_week(monday, friday),
            'institutional_summary': self.analyze_institutional_week(monday, friday),
            'technical_summary': self.analyze_technical_week(monday, friday),
            'market_summary': {}
        }
        
        # 生成市場總結
        self.generate_market_summary(summary_data)
        
        # 儲存週度摘要
        self.save_weekly_summary(summary_data)
        
        # 顯示摘要
        self.display_weekly_summary(summary_data)
        
        return summary_data
    
    def get_week_data(self, start_date, end_date):
        """獲取週內 JSON 資料"""
        data_files = sorted(glob.glob(os.path.join(self.data_dir, "market_data_tw_*.json")))
        week_data = []
        
        for file in data_files:
            try:
                file_date = file.split('market_data_tw_')[1].replace('.json', '')
                if start_date.strftime('%Y-%m-%d') <= file_date <= end_date.strftime('%Y-%m-%d'):
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        week_data.append(data)
            except Exception as e:
                logger.error(f"❌ 讀取 {file} 錯誤: {e}")
        
        return sorted(week_data, key=lambda x: x['date'])
    
    def analyze_taiex_week(self, start_date, end_date):
        """分析週內加權指數表現"""
        week_data = self.get_week_data(start_date, end_date)
        
        if not week_data:
            logger.warning("無 TAIEX 數據可用")
            return None
        
        first_day = week_data[0]
        last_day = week_data[-1]
        
        weekly_change = last_day['taiex']['closing_price'] - first_day['taiex']['closing_price']
        weekly_change_pct = (weekly_change / first_day['taiex']['closing_price']) * 100
        
        closing_prices = [d['taiex']['closing_price'] for d in week_data]
        volumes = [d['trading_volume'] for d in week_data]
        change_points = [
            d['taiex']['closing_price'] - week_data[i-1]['taiex']['closing_price']
            if i > 0 else 0
            for i, d in enumerate(week_data)
        ]
        
        return {
            'trading_days': len(week_data),
            'week_start_index': first_day['taiex']['closing_price'],
            'week_end_index': last_day['taiex']['closing_price'],
            'weekly_change': round(weekly_change, 2),
            'weekly_change_percent': round(weekly_change_pct, 2),
            'highest_index': max(closing_prices),
            'lowest_index': min(closing_prices),
            'total_volume': round(sum(volumes), 2),
            'avg_daily_volume': round(sum(volumes) / len(volumes), 2) if volumes else 0,
            'up_days': len([c for c in change_points if c > 0]),
            'down_days': len([c for c in change_points if c < 0]),
            'flat_days': len([c for c in change_points if c == 0])
        }
    
    def analyze_institutional_week(self, start_date, end_date):
        """分析週內三大法人動向"""
        week_data = self.get_week_data(start_date, end_date)
        
        if not week_data:
            logger.warning("無三大法人數據可用")
            return None
        
        investors = ['foreign_investors', 'investment_trust', 'dealers']
        summary = {}
        
        for investor in investors:
            total_net = sum(d['institutional_investors'][investor] for d in week_data)
            buy_days = len([d for d in week_data if d['institutional_investors'][investor] > 0])
            sell_days = len([d for d in week_data if d['institutional_investors'][investor] < 0])
            avg_daily = total_net / len(week_data) if week_data else 0
            
            summary[investor] = {
                'total_net_buy': round(total_net, 2),
                'buy_days': buy_days,
                'sell_days': sell_days,
                'avg_daily': round(avg_daily, 2),
                'direction': '淨買超' if total_net > 0 else '淨賣超' if total_net < 0 else '持平'
            }
        
        total_net = sum(d['institutional_investors']['foreign_investors'] +
                       d['institutional_investors']['investment_trust'] +
                       d['institutional_investors']['dealers'] for d in week_data)
        summary['total_institutional'] = {
            'total_net_buy': round(total_net, 2),
            'direction': '淨買超' if total_net > 0 else '淨賣超' if total_net < 0 else '持平'
        }
        
        return summary
    
    def analyze_technical_week(self, start_date, end_date):
        """分析週內技術指標"""
        week_data = self.get_week_data(start_date, end_date)
        
        if not week_data:
            logger.warning("無技術指標數據可用")
            return None
        
        last_day = week_data[-1]
        ma5_values = [d['moving_averages']['ma5'] for d in week_data]
        ma10_values = [d['moving_averages']['ma10'] for d in week_data]
        histogram_values = [d['macd']['histogram'] for d in week_data]
        
        return {
            'ma5': last_day['moving_averages']['ma5'],
            'ma10': last_day['moving_averages']['ma10'],
            'ma20': last_day['moving_averages']['ma20'],
            'macd_histogram': last_day['macd']['histogram'],
            'ma5_trend': '上升' if ma5_values[-1] > ma5_values[0] else '下降',
            'technical_trend': '看多' if histogram_values[-1] > 0 else '看空'
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
            
            if 'total_institutional' in institutional:
                total_net = institutional['total_institutional']['total_net_buy']
                if total_net > 100:
                    market_summary['key_highlights'].append(f"三大法人週淨買超 {total_net:.0f} 億元")
                    market_summary['opportunities'].append("法人資金持續流入")
                elif total_net < -100:
                    market_summary['risk_factors'].append(f"三大法人週淨賣超 {abs(total_net):.0f} 億元")
            
            if 'foreign_investors' in institutional:
                foreign_net = institutional['foreign_investors']['total_net_buy']
                if foreign_net > 50:
                    market_summary['opportunities'].append("外資持續買超")
                elif foreign_net < -50:
                    market_summary['risk_factors'].append("外資持續賣超")
        
        # 分析技術指標
        if summary_data['technical_summary']:
            technical = summary_data['technical_summary']
            if technical['macd_histogram'] > 0:
                market_summary['opportunities'].append("MACD 顯示看多訊號")
            elif technical['macd_histogram'] < 0:
                market_summary['risk_factors'].append("MACD 顯示看空訊號")
            if technical['ma5'] > technical['ma10'] > technical['ma20']:
                market_summary['opportunities'].append("均線多頭排列")
            elif technical['ma5'] < technical['ma10'] < technical['ma20']:
                market_summary['risk_factors'].append("均線空頭排列")
        
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
        week_str = f"{summary_data['week_start'].replace('-', '')}_{summary_data['week_end'].replace('-', '')}"
        json_file = f"{self.data_dir}/weekly_summary_{week_str}.json"
        
        os.makedirs(self.data_dir, exist_ok=True)
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 週度摘要已儲存: {json_file}")
    
    def display_weekly_summary(self, summary_data):
        """顯示週度摘要"""
        logger.info(f"\n📊 週度市場摘要 ({summary_data['week_start']} ~ {summary_data['week_end']})")
        logger.info("=" * 70)
        
        # 加權指數週表現
        if summary_data['taiex_summary']:
            taiex = summary_data['taiex_summary']
            logger.info(f"📈 台灣加權指數週表現:")
            logger.info(f"   週初: {taiex['week_start_index']:,.2f}")
            logger.info(f"   週末: {taiex['week_end_index']:,.2f}")
            logger.info(f"   週漲跌: {taiex['weekly_change']:+.2f} ({taiex['weekly_change_percent']:+.2f}%)")
            logger.info(f"   週高低: {taiex['highest_index']:,.2f} / {taiex['lowest_index']:,.2f}")
            logger.info(f"   成交日: {taiex['up_days']}漲 {taiex['down_days']}跌 {taiex['flat_days']}平")
            logger.info(f"   週成交額: {taiex['total_volume']:,.0f} 億元")
        
        # 三大法人週動向
        if summary_data['institutional_summary']:
            logger.info(f"\n💰 三大法人週買賣超:")
            institutional = summary_data['institutional_summary']
            
            for investor in ['foreign_investors', 'investment_trust', 'dealers']:
                if investor in institutional:
                    data = institutional[investor]
                    investor_name = {'foreign_investors': '外資及陸資', 'investment_trust': '投信', 'dealers': '自營商'}[investor]
                    logger.info(f"   {investor_name}: {data['direction']} {abs(data['total_net_buy']):.0f} 億元 ({data['buy_days']}買 {data['sell_days']}賣)")
            
            if 'total_institutional' in institutional:
                total = institutional['total_institutional']
                logger.info(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                logger.info(f"   三大法人合計: {total['direction']} {abs(total['total_net_buy']):.0f} 億元")
        
        # 技術指標
        if summary_data['technical_summary']:
            technical = summary_data['technical_summary']
            logger.info(f"\n📉 技術指標週表現:")
            logger.info(f"   MA5: {technical['ma5']:,.2f}")
            logger.info(f"   MA10: {technical['ma10']:,.2f}")
            logger.info(f"   MA20: {technical['ma20']:,.2f}")
            logger.info(f"   MACD Histogram: {technical['macd_histogram']:.2f} ({technical['technical_trend']})")
        
        # 市場總結
        if summary_data['market_summary']:
            market = summary_data['market_summary']
            logger.info(f"\n🎯 市場週度總結:")
            logger.info(f"   整體情緒: {market['overall_sentiment']}")
            
            if market['key_highlights']:
                logger.info(f"   重點表現: {'; '.join(market['key_highlights'])}")
            
            if market['opportunities']:
                logger.info(f"   正面因素: {'; '.join(market['opportunities'])}")
            
            if market['risk_factors']:
                logger.info(f"   風險因素: {'; '.join(market['risk_factors'])}")
        
        logger.info(f"\n⏰ 摘要生成時間: {summary_data['generated_time']}")

def main():
    logger.info("📅 台股週度摘要生成器啟動")
    logger.info("=" * 50)
    
    generator = WeeklySummaryGenerator()
    
    try:
        summary = generator.generate_weekly_summary()
        
        if summary:
            logger.info("\n✅ 週度摘要生成完成")
        else:
            logger.warning("\n⚠️  無法生成週度摘要")
            
    except Exception as e:
        logger.error(f"\n❌ 週度摘要生成錯誤: {e}")

if __name__ == "__main__":
    main()