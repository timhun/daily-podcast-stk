#!/usr/bin/env python3
“””
內容創作師 (Content Creator Genius)
AI驅動的專業播客文字稿創作引擎

Author: 幫幫忙 AI
Version: 1.0.0
“””

import json
import requests
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os
import random

# 配置日誌

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(**name**)

class GrokAPIClient:
“”“Grok API客戶端”””

```
def __init__(self, api_key: str = None):
    self.api_key = api_key or os.getenv('GROK_API_KEY', 'your-grok-api-key')
    self.base_url = "https://api.x.ai/v1"
    self.headers = {
        'Authorization': f'Bearer {self.api_key}',
        'Content-Type': 'application/json'
    }

def generate_content(self, prompt: str, max_tokens: int = 3000, temperature: float = 0.7) -> str:
    """調用Grok API生成內容"""
    try:
        payload = {
            'model': 'grok-beta',
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': max_tokens,
            'temperature': temperature
        }
        
        response = requests.post(
            f'{self.base_url}/chat/completions',
            headers=self.headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            logger.error(f"Grok API錯誤: {response.status_code} - {response.text}")
            return self._fallback_content_generation(prompt)
            
    except Exception as e:
        logger.error(f"Grok API調用失敗: {e}")
        return self._fallback_content_generation(prompt)

def _fallback_content_generation(self, prompt: str) -> str:
    """備用內容生成（當API失敗時）"""
    logger.warning("使用備用內容生成器")
    return """
```

各位投資朋友大家好，我是幫幫忙。

由於技術問題，今天的內容生成遇到了一些困難。
不過別擔心，我們的系統正在努力修復中。

請稍後再次收聽，我們會為您帶來最專業的投資分析。

感謝您的耐心等待，我們明天見！
“””

class TemplateManager:
“”“模板管理器”””

```
def __init__(self):
    self.templates = {
        'tw': self._load_tw_template(),
        'us': self._load_us_template()
    }
    self.investment_quotes = self._load_investment_quotes()

def _load_tw_template(self) -> str:
    """台股版本模板"""
    return """
```

# 台股播客文字稿模板

## 開場白 (30秒)

各位投資朋友大家下午好，我是幫幫忙，歡迎收聽《幫幫忙說財經科技投資》。
今天是{date}，台股剛剛收盤，讓我們來看看今天的市場表現。

## 市場概況 (90秒)

{market_summary}

## 技術分析深度解讀 (180秒)

{technical_analysis}

## 產業動態焦點 (120秒)

{industry_news}

## 投資金句結尾 (30秒)

{closing_quote}

今天的分析就到這裡，明天我們再見！
“””

```
def _load_us_template(self) -> str:
    """美股版本模板"""
    return """
```

# 美股播客文字稿模板

## 開場白 (30秒)

各位投資朋友大家早安，我是幫幫忙，為您帶來美股收盤分析。
這裡是{date}的《幫幫忙說財經科技投資》。

## 美股三大指數 (90秒)

{market_summary}

## 科技股焦點 (180秒)

{tech_analysis}

## 大宗商品與避險 (90秒)

{commodities_analysis}

## 投資智慧結尾 (30秒)

{closing_quote}

感謝收聽，我們明天見！
“””

```
def _load_investment_quotes(self) -> List[Dict]:
    """載入投資大師名言"""
    return [
        {
            "author": "André Kostolany",
            "quote": "有錢的人，可以投機；錢少的人，不可以投機；根本沒錢的人，必須投機。",
            "context": "投機與投資的智慧"
        },
        {
            "author": "Warren Buffett", 
            "quote": "在別人恐懼時貪婪，在別人貪婪時恐懼。",
            "context": "逆向投資思維"
        },
        {
            "author": "Peter Lynch",
            "quote": "投資你了解的公司，避開你不懂的領域。",
            "context": "能力圈投資法則"
        },
        {
            "author": "Benjamin Graham",
            "quote": "投資的藝術在於，以40分錢的價格買入價值1美元的股票。",
            "context": "價值投資精髓"
        },
        {
            "author": "Ray Dalio",
            "quote": "成功的投資是一門藝術，需要平衡風險與報酬。",
            "context": "風險管理哲學"
        }
    ]

def get_template(self, mode: str) -> str:
    """獲取模板"""
    return self.templates.get(mode, self.templates['tw'])

def get_random_quote(self) -> Dict:
    """獲取隨機投資名言"""
    return random.choice(self.investment_quotes)
```

class ContentCreatorGenius:
“”“內容創作師主類”””

```
def __init__(self, grok_api_key: str = None):
    self.grok_client = GrokAPIClient(grok_api_key)
    self.template_manager = TemplateManager()
    self.style_guide = self._load_style_guide()

def _load_style_guide(self) -> Dict:
    """載入寫作風格指南"""
    return {
        'tone': '專業但親和的台灣用語',
        'technical_terms': '適度使用，避免過於艱深',
        'ai_terms': '直接使用英文 (如 AI, LLM, Agent)',
        'length_target': '3000字以內',
        'format': '純文字稿，無額外格式標記',
        'audience': '個人投資者、科技業從業者',
        'key_principles': [
            '數據驅動，避免主觀猜測',
            '風險提示，負責任建議',
            '教育導向，提升投資知識',
            '本土化表達，貼近台灣投資人'
        ]
    }

def generate_script(self, market_data: Dict, analysis_result: Dict, 
                   news_data: Dict, mode: str = 'tw', date: str = None) -> Dict:
    """生成播客文字稿"""
    logger.info(f"開始生成{mode.upper()}播客文字稿")
    
    if not date:
        date = datetime.now().strftime('%Y年%m月%d日')
    
    try:
        # 1. 數據整合與結構化
        structured_data = self._structure_data(market_data, analysis_result, news_data, mode)
        
        # 2. 生成各個段落
        if mode == 'tw':
            script_content = self._generate_tw_script(structured_data, date)
        else:
            script_content = self._generate_us_script(structured_data, date)
        
        # 3. 內容優化與潤色
        optimized_content = self._optimize_content(script_content, mode)
        
        # 4. 品質檢查
        quality_check = self._quality_check(optimized_content, mode)
        
        return {
            'success': True,
            'script': optimized_content,
            'metadata': {
                'date': date,
                'mode': mode,
                'word_count': len(optimized_content),
                'estimated_duration': self._estimate_duration(optimized_content),
                'quality_score': quality_check['score'],
                'generation_time': datetime.now().isoformat()
            },
            'quality_check': quality_check
        }
        
    except Exception as e:
        logger.error(f"文字稿生成失敗: {e}")
        return {
            'success': False,
            'error': str(e),
            'fallback_script': self._generate_fallback_script(mode, date)
        }

def _structure_data(self, market_data: Dict, analysis_result: Dict, 
                   news_data: Dict, mode: str) -> Dict:
    """結構化數據整理"""
    structured = {
        'market_summary': {},
        'technical_analysis': {},
        'strategy_signals': {},
        'news_highlights': {},
        'risk_assessment': {}
    }
    
    # 整理市場數據
    if market_data:
        structured['market_summary'] = self._extract_market_summary(market_data, mode)
    
    # 整理分析結果
    if analysis_result:
        if 'technical_score' in analysis_result:
            structured['technical_analysis'] = analysis_result['technical_score']
        
        if 'final_recommendation' in analysis_result:
            structured['strategy_signals'] = analysis_result['final_recommendation']
        
        if 'risk_assessment' in analysis_result:
            structured['risk_assessment'] = analysis_result['risk_assessment']
    
    # 整理新聞數據
    if news_data:
        structured['news_highlights'] = self._extract_news_highlights(news_data, mode)
    
    return structured

def _extract_market_summary(self, market_data: Dict, mode: str) -> Dict:
    """提取市場摘要"""
    summary = {}
    
    if mode == 'tw':
        # 台股相關數據
        symbols = ['^TWII', '0050.TW', '2330.TW']
    else:
        # 美股相關數據
        symbols = ['^GSPC', '^IXIC', '^DJI', 'QQQ', 'SPY']
    
    for symbol in symbols:
        if symbol in market_data:
            data = market_data[symbol]
            if 'Close' in data and len(data['Close']) > 1:
                current_price = data['Close'][-1]
                prev_price = data['Close'][-2]
                change_pct = ((current_price - prev_price) / prev_price) * 100
                
                summary[symbol] = {
                    'current_price': round(current_price, 2),
                    'change_pct': round(change_pct, 2),
                    'volume': data.get('Volume', [0])[-1] if 'Volume' in data else 0
                }
    
    return summary

def _extract_news_highlights(self, news_data: Dict, mode: str) -> List[Dict]:
    """提取新聞亮點"""
    highlights = []
    
    # 根據模式選擇相應的新聞
    news_key = 'taiwan_news' if mode == 'tw' else 'global_news'
    
    if news_key in news_data:
        news_items = news_data[news_key][:3]  # 取前3條重要新聞
        
        for item in news_items:
            highlights.append({
                'title': item.get('title', ''),
                'summary': item.get('summary', '')[:200],  # 限制長度
                'impact': self._assess_news_impact(item.get('title', ''))
            })
    
    return highlights

def _assess_news_impact(self, title: str) -> str:
    """評估新聞影響"""
    positive_keywords = ['上漲', '成長', '獲利', '突破', '創新高', '利多']
    negative_keywords = ['下跌', '虧損', '警告', '風險', '創新低', '利空']
    
    title_lower = title.lower()
    
    if any(keyword in title_lower for keyword in positive_keywords):
        return 'positive'
    elif any(keyword in title_lower for keyword in negative_keywords):
        return 'negative'
    else:
        return 'neutral'

def _generate_tw_script(self, structured_data: Dict, date: str) -> str:
    """生成台股版文字稿"""
    # 構建Grok API提示詞
    prompt = f"""
```

你是專業的財經播客主持人「幫幫忙」，請基於以下數據生成台股播客文字稿：

日期：{date}
模式：台股版本 (下午2點播出)

市場數據：
{json.dumps(structured_data[‘market_summary’], ensure_ascii=False, indent=2)}

技術分析：
{json.dumps(structured_data[‘technical_analysis’], ensure_ascii=False, indent=2)}

策略信號：
{json.dumps(structured_data[‘strategy_signals’], ensure_ascii=False, indent=2)}

風險評估：
{json.dumps(structured_data[‘risk_assessment’], ensure_ascii=False, indent=2)}

新聞亮點：
{json.dumps(structured_data[‘news_highlights’], ensure_ascii=False, indent=2)}

請按照以下架構生成7分鐘的播客文字稿（約3000字）：

1. 開場白 (30秒)
- 親切問候，介紹今日主題
1. 市場概況 (90秒)
- 台股加權指數表現
- 0050 ETF 動態
- 權值股重點分析
1. 技術分析深度解讀 (180秒)
- AI策略大師推薦解析
- 0050技術指標分析
- 具體進場時機與風險控制
- 倉位管理建議
1. 產業動態焦點 (120秒)
- 重點財經新聞解讀
- 科技產業趨勢分析
- 政策面影響評估
1. 投資金句結尾 (30秒)
- 投資大師智慧分享
- 明日展望

寫作要求：

- 使用專業但親和的台灣用語
- 避免過於複雜的技術術語
- 數據要具體，分析要客觀
- 必須包含風險提示
- 語調自然，適合語音播放
- 總字數控制在3000字以內

請開始生成文字稿：
“””

```
    return self.grok_client.generate_content(prompt, max_tokens=3500, temperature=0.7)

def _generate_us_script(self, structured_data: Dict, date: str) -> str:
    """生成美股版文字稿"""
    prompt = f"""
```

你是專業的財經播客主持人「幫幫忙」，請基於以下數據生成美股播客文字稿：

日期：{date}
模式：美股版本 (早上6點播出)

市場數據：
{json.dumps(structured_data[‘market_summary’], ensure_ascii=False, indent=2)}

技術分析：
{json.dumps(structured_data[‘technical_analysis’], ensure_ascii=False, indent=2)}

策略信號：
{json.dumps(structured_data[‘strategy_signals’], ensure_ascii=False, indent=2)}

風險評估：
{json.dumps(structured_data[‘risk_assessment’], ensure_ascii=False, indent=2)}

新聞亮點：
{json.dumps(structured_data[‘news_highlights’], ensure_ascii=False, indent=2)}

請按照以下架構生成7分鐘的播客文字稿（約3000字）：

1. 開場白 (30秒)
- 早安問候，美股收盤分析預告
1. 美股三大指數 (90秒)
- 道瓊、納斯達克、S&P500分析
- 科技股與傳統產業對比
- VIX恐慌指數解讀
1. 科技股焦點 (180秒)
- QQQ ETF 深度技術分析
- FAANG股票與AI概念股動態
- 量化策略信號與交易建議
- 比特幣關聯分析
1. 大宗商品與避險 (90秒)
- 黃金價格走勢分析
- 原油市場動態
- 美債殖利率影響
1. 投資智慧結尾 (30秒)
- 大師金句與投資哲學

寫作要求：

- 專業但易懂的財經用語
- 重點關注科技股與創新趨勢
- 數據驅動的客觀分析
- 全球視野的投資建議
- 適合台灣投資人的本土化表達
- 總字數控制在3000字以內

請開始生成文字稿：
“””

```
    return self.grok_client.generate_content(prompt, max_tokens=3500, temperature=0.7)

def _optimize_content(self, raw_content: str, mode: str) -> str:
    """內容優化與潤色"""
    logger.info("開始內容優化處理")
    
    # 基本清理
    content = raw_content.strip()
    
    # 移除多餘的格式標記
    content = re.sub(r'#+\s*', '', content)  # 移除markdown標題
    content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # 移除粗體標記
    content = re.sub(r'\*(.*?)\*', r'\1', content)  # 移除斜體標記
    
    # 段落優化
    content = re.sub(r'\n{3,}', '\n\n', content)  # 限制空行數量
    content = re.sub(r'[ \t]+', ' ', content)  # 規範化空格
    
    # 添加語音停頓標記
    content = self._add_speech_markers(content)
    
    # 確保結尾完整
    if not content.endswith(('。', '！', '？')):
        content += '。'
    
    # 添加投資免責聲明
    content = self._add_disclaimer(content, mode)
    
    return content

def _add_speech_markers(self, content: str) -> str:
    """添加語音停頓標記"""
    # 在句號後添加短暫停頓
    content = content.replace('。', '。<break time="300ms"/>')
    
    # 在重要轉折處添加停頓
    transitions = ['不過', '然而', '另外', '此外', '總的來說', '需要注意的是']
    for transition in transitions:
        content = content.replace(transition, f'<break time="200ms"/>{transition}')
    
    # 在數字後添加微停頓
    content = re.sub(r'(\d+(?:\.\d+)?%)', r'\1<break time="100ms"/>', content)
    
    return content

def _add_disclaimer(self, content: str, mode: str) -> str:
    """添加投資免責聲明"""
    disclaimer = """
```

最後提醒大家，以上內容僅供參考，不構成投資建議。
投資有風險，請根據自身情況謹慎決策。”””

```
    return content + disclaimer

def _quality_check(self, content: str, mode: str) -> Dict:
    """內容品質檢查"""
    logger.info("執行內容品質檢查")
    
    checks = {
        'word_count': len(content),
        'estimated_duration': self._estimate_duration(content),
        'contains_data': bool(re.search(r'\d+(?:\.\d+)?%', content)),
        'contains_disclaimer': '僅供參考' in content,
        'paragraph_balance': self._check_paragraph_balance(content),
        'readability': self._assess_readability(content)
    }
    
    # 計算綜合品質分數
    score = 0
    max_score = 0
    
    # 字數檢查 (2500-3500字為佳)
    word_count = checks['word_count']
    if 2500 <= word_count <= 3500:
        score += 25
    elif 2000 <= word_count <= 4000:
        score += 15
    else:
        score += 5
    max_score += 25
    
    # 時長檢查 (6-8分鐘為佳)
    duration = checks['estimated_duration']
    if 6 <= duration <= 8:
        score += 20
    elif 5 <= duration <= 9:
        score += 15
    else:
        score += 5
    max_score += 20
    
    # 內容檢查
    if checks['contains_data']:
        score += 15
    max_score += 15
    
    if checks['contains_disclaimer']:
        score += 10
    max_score += 10
    
    if checks['paragraph_balance']:
        score += 15
    max_score += 15
    
    if checks['readability'] > 0.7:
        score += 15
    elif checks['readability'] > 0.5:
        score += 10
    else:
        score += 5
    max_score += 15
    
    final_score = (score / max_score) * 100
    
    return {
        'score': round(final_score, 1),
        'checks': checks,
        'recommendations': self._generate_recommendations(checks)
    }

def _estimate_duration(self, content: str) -> float:
    """估計播放時長（分鐘）"""
    # 中文平均閱讀速度約200字/分鐘，語音播放稍慢約150字/分鐘
    chars_per_minute = 150
    return len(content) / chars_per_minute

def _check_paragraph_balance(self, content: str) -> bool:
    """檢查段落平衡"""
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    
    if len(paragraphs) < 3:
        return False
    
    # 檢查段落長度分佈
    lengths = [len(p) for p in paragraphs]
    avg_length = sum(lengths) / len(lengths)
    
    # 檢查是否有過長或過短的段落
    balanced = all(avg_length * 0.3 < length < avg_length * 2.5 for length in lengths)
    
    return balanced

def _assess_readability(self, content: str) -> float:
    """評估可讀性"""
    # 簡化的可讀性評估
    sentences = re.split(r'[。！？]', content)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return 0
    
    # 平均句長
    avg_sentence_length = sum(len(s) for s in sentences) / len(sentences)
    
    # 句長評分 (15-30字為佳)
    if 15 <= avg_sentence_length <= 30:
        length_score = 1.0
    elif 10 <= avg_sentence_length <= 40:
        length_score = 0.8
    else:
        length_score = 0.5
    
    # 複雜詞彙檢查
    complex_terms = ['量化', '技術指標', '波動率', '流動性']
    complex_count = sum(content.count(term) for term in complex_terms)
    complexity_ratio = complex_count / len(sentences)
    
    # 複雜度評分 (適度使用專業術語)
    if complexity_ratio < 0.5:
        complexity_score = 1.0
    elif complexity_ratio < 1.0:
        complexity_score = 0.8
    else:
        complexity_score = 0.6
    
    return (length_score + complexity_score) / 2

def _generate_recommendations(self, checks: Dict) -> List[str]:
    """生成改進建議"""
    recommendations = []
    
    word_count = checks['word_count']
    duration = checks['estimated_duration']
    
    if word_count < 2500:
        recommendations.append("內容稍短，建議增加更多分析細節")
    elif word_count > 3500:
        recommendations.append("內容較長，建議適當精簡")
    
    if duration < 6:
        recommendations.append("播放時長偏短，建議增加內容深度")
    elif duration > 8:
        recommendations.append("播放時長偏長，建議提高內容密度")
    
    if not checks['contains_data']:
        recommendations.append("缺少具體數據支撐，建議添加更多量化信息")
    
    if not checks['paragraph_balance']:
        recommendations.append("段落結構不均衡，建議調整內容分配")
    
    if checks['readability'] < 0.7:
        recommendations.append("可讀性有待提升，建議簡化複雜表達")
    
    if not recommendations:
        recommendations.append("內容品質良好，可以直接使用")
    
    return recommendations

def _generate_fallback_script(self, mode: str, date: str) -> str:
    """生成備用文字稿"""
    quote = self.template_manager.get_random_quote()
    
    market_name = "台股" if mode == 'tw' else "美股"
    time_greeting = "下午好" if mode == 'tw' else "早安"
    
    return f"""
```

各位投資朋友{time_greeting}，我是幫幫忙。

今天是{date}，歡迎收聽《幫幫忙說財經科技投資》。

由於技術原因，今天的詳細{market_name}分析暫時無法為您呈現。
不過，我們的系統正在努力修復中，明天將為您帶來更完整的分析。

在此，我想與大家分享一句投資智慧：

{quote[‘author’]}曾經說過：「{quote[‘quote’]}」

這提醒我們，{quote[‘context’]}是投資成功的重要因素。

感謝您的收聽，我們明天見！

以上內容僅供參考，不構成投資建議。投資有風險，請謹慎決策。
“””

```
def save_script(self, script_data: Dict, output_path: str = None) -> str:
    """保存文字稿"""
    if not output_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        mode = script_data.get('metadata', {}).get('mode', 'unknown')
        output_path = f"episodes/{timestamp}_{mode}/script.txt"
    
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 保存文字稿
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(script_data.get('script', ''))
        
        # 保存metadata
        metadata_path = output_path.replace('script.txt', 'metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(script_data.get('metadata', {}), f, 
                     ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"文字稿已保存: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"文字稿保存失敗: {e}")
        raise
```

def main():
“”“主程序示例”””
import argparse
import sys

```
parser = argparse.ArgumentParser(description='內容創作師 - AI播客文字稿生成')
parser.add_argument('--mode', type=str, choices=['tw', 'us'], 
                   required=True, help='播客模式')
parser.add_argument('--date', type=str, help='播客日期 (YYYYMMDD)')
parser.add_argument('--market-data', type=str, help='市場數據JSON文件路徑')
parser.add_argument('--analysis-result', type=str, help='分析結果JSON文件路徑')
parser.add_argument('--news-data', type=str, help='新聞數據JSON文件路徑')
parser.add_argument('--grok-api-key', type=str, help='Grok API密鑰')

args = parser.parse_args()

# 處理日期
if args.date:
    try:
        date_obj = datetime.strptime(args.date, '%Y%m%d')
        formatted_date = date_obj.strftime('%Y年%m月%d日')
    except ValueError:
        logger.error("日期格式錯誤，應為YYYYMMDD")
        sys.exit(1)
else:
    formatted_date = datetime.now().strftime('%Y年%m月%d日')

# 載入數據
market_data = {}
analysis_result = {}
news_data = {}

if args.market_data and os.path.exists(args.market_data):
    with open(args.market_data, 'r', encoding='utf-8') as f:
        market_data = json.load(f)

if args.analysis_result and os.path.exists(args.analysis_result):
    with open(args.analysis_result, 'r', encoding='utf-8') as f:
        analysis_result = json.load(f)

if args.news_data and os.path.exists(args.news_data):
    with open(args.news_data, 'r', encoding='utf-8') as f:
        news_data = json.load(f)

# 初始化內容創作師
creator = ContentCreatorGenius(grok_api_key=args.grok_api_key)

# 生成文字稿
logger.info(f"開始生成{args.mode.upper()}播客文字稿")
result = creator.generate_script(
    market_data=market_data,
    analysis_result=analysis_result,
    news_data=news_data,
    mode=args.mode,
    date=formatted_date
)

if result['success']:
    # 保存文字稿
    output_path = creator.save_script(result)
    
    # 輸出摘要
    metadata = result['metadata']
    quality = result['quality_check']
    
    print(f"\n=== 文字稿生成完成 ===")
    print(f"模式: {args.mode.upper()}")
    print(f"日期: {formatted_date}")
    print(f"字數: {metadata['word_count']}")
    print(f"預估時長: {metadata['estimated_duration']:.1f}分鐘")
    print(f"品質評分: {quality['score']}")
    print(f"輸出路徑: {output_path}")
    
    if quality['recommendations']:
        print("\n改進建議:")
        for rec in quality['recommendations']:
            print(f"- {rec}")
    
else:
    print(f"文字稿生成失敗: {result['error']}")
    if 'fallback_script' in result:
        print("已生成備用文字稿")
```

if **name** == “**main**”:
main()