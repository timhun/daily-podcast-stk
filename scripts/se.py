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
```