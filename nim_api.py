#!/usr/bin/env python3
"""
nim_api.py - 統一 LLM API 封裝 (NIM: NVIDIA Inference Microservice)

功能：
- 支援多 Provider 自動 failover（NVIDIA > xAI > Gemini > Groq > OpenAI > OpenRouter）
- 任務分類自動選模型（快速任務用小模型，複雜任務用大模型）
- 速率限制保護（40 RPM NVIDIA API）
- 任務鏈 (Task Chain) 支援

用法：
    from nim_api import call_nim, optimize_script_with_nim
    
    # 簡單呼叫
    result = call_nim("今天市場分析", task_type="quick")
    
    # 進階：指定 model
    result = call_nim("分析策略", model="glm-5.1", task_type="deep")
    
    # 任務鏈
    from nim_api import TaskChain
    chain = TaskChain()
    result = chain.then("收集數據").then("分析").then("生成腳本").execute()
"""

import os
import json
import time
import logging
from typing import Optional, Dict, List, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nim_api")

# ============================================================================
# Configuration
# ============================================================================

@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    provider: str
    endpoint: str
    api_key_env: str
    max_tokens: int = 4096
    supports_thinking: bool = False
    supports_tools: bool = False
    cost_tier: int = 1  # 1=free/fast, 2=paid, 3=expensive
    latency_tier: int = 1  # 1=fast (<5s), 2=medium (<30s), 3=slow (>30s)

# 可用模型列表
MODELS = {
    # NVIDIA Free Models (40 RPM limit)
    "llama-3.3-70b": ModelConfig(
        name="meta/llama-3.3-70b-instruct",
        provider="nvidia",
        endpoint="https://integrate.api.nvidia.com/v1",
        api_key_env="NVIDIA_API_KEY",
        max_tokens=8192,
        supports_tools=True,
        cost_tier=1,
        latency_tier=2
    ),
    "glm-5.1": ModelConfig(
        name="z-ai/glm-5.1",
        provider="nvidia",
        endpoint="https://integrate.api.nvidia.com/v1",
        api_key_env="NVIDIA_API_KEY",
        max_tokens=8192,
        supports_thinking=True,
        cost_tier=1,
        latency_tier=3
    ),
    "deepseek-v3.2": ModelConfig(
        name="deepseek-ai/deepseek-v3-0324",
        provider="nvidia",
        endpoint="https://integrate.api.nvidia.com/v1",
        api_key_env="NVIDIA_API_KEY",
        max_tokens=8192,
        supports_thinking=True,
        cost_tier=1,
        latency_tier=3
    ),
    "qwen-3.5": ModelConfig(
        name="qwen/qwen3-32b",
        provider="nvidia",
        endpoint="https://integrate.api.nvidia.com/v1",
        api_key_env="NVIDIA_API_KEY",
        max_tokens=4096,
        cost_tier=1,
        latency_tier=2
    ),
    
    # xAI Grok
    "grok-4": ModelConfig(
        name="grok-4",
        provider="xai",
        endpoint="https://api.x.ai/v1",
        api_key_env="XAI_API_KEY",
        max_tokens=4096,
        supports_thinking=True,
        cost_tier=3,
        latency_tier=2
    ),
    "grok-beta": ModelConfig(
        name="grok-beta",
        provider="xai",
        endpoint="https://api.x.ai/v1",
        api_key_env="XAI_API_KEY",
        max_tokens=2048,
        cost_tier=2,
        latency_tier=1
    ),
    
    # Google Gemini
    "gemini-2.0-flash": ModelConfig(
        name="gemini-2.0-flash-exp",
        provider="gemini",
        endpoint="https://generativelanguage.googleapis.com",
        api_key_env="GEMINI_API_KEY",
        max_tokens=8192,
        cost_tier=1,
        latency_tier=1
    ),
    
    # Groq (Free, fast)
    "llama-3.1-8b": ModelConfig(
        name="llama-3.1-8b-instant",
        provider="groq",
        endpoint="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
        max_tokens=4096,
        cost_tier=1,
        latency_tier=1
    ),
    "llama-3.1-70b": ModelConfig(
        name="llama-3.3-70b-versatile",
        provider="groq",
        endpoint="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
        max_tokens=8192,
        cost_tier=1,
        latency_tier=1
    ),
    
    # OpenAI
    "gpt-4o-mini": ModelConfig(
        name="gpt-4o-mini",
        provider="openai",
        endpoint="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        max_tokens=4096,
        cost_tier=2,
        latency_tier=1
    ),
    
    # OpenRouter (aggregator)
    "openrouter-gemini": ModelConfig(
        name="google/gemini-2.0-flash-exp:free",
        provider="openrouter",
        endpoint="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        max_tokens=4096,
        cost_tier=1,
        latency_tier=1
    ),
    # Google Gemini 3.1 Flash Lite (fastest, no rate limit)
    "gemini-3.1-flash-lite": ModelConfig(
        name="gemini-3.1-flash-lite",
        provider="gemini",
        endpoint="https://generativelanguage.googleapis.com",
        api_key_env="GEMINI_API_KEY",
        max_tokens=8192,
        cost_tier=1,
        latency_tier=1
    ),
    # Google Gemini 2.5 Flash (more capable, rate limited)
    "gemini-2.5-flash": ModelConfig(
        name="gemini-2.5-flash",
        provider="gemini",
        endpoint="https://generativelanguage.googleapis.com",
        api_key_env="GEMINI_API_KEY",
        max_tokens=8192,
        cost_tier=1,
        latency_tier=2
    ),

}

# 任務類型 → 推薦模型
TASK_MODEL_MAP = {
    "quick": ["gemini-3.1-flash-lite", "gemini-2.5-flash", "llama-3.3-70b", "qwen-3.5", "grok-beta", "qwen3.6-ollama"],
    "medium": ["gemini-3.1-flash-lite", "gemini-2.5-flash", "llama-3.3-70b", "deepseek-v3.2"],
    "deep": ["glm-5.1", "deepseek-v3.2", "grok-4"],
    "script": ["llama-3.3-70b", "glm-5.1"],  # Podcast 腳本生成
    "strategy": ["glm-5.1", "deepseek-v3.2"],  # 策略分析
    "json": ["llama-3.3-70b", "qwen-3.5", "grok-4"],  # JSON 输出
}


def _call_ollama(prompt, model_key="qwen3.6-ollama", system=None,
                 temperature=0.7, max_tokens=None, **kwargs):
    """Call local Ollama API (no API key, ~30s, last resort)"""
    model = MODELS.get(model_key, MODELS.get("qwen3.6-ollama"))
    max_tokens = max_tokens or model.max_tokens
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        import httpx
        with httpx.Client(timeout=60) as client:
            r = client.post(f"{model.endpoint}/v1/chat/completions",
                json={"model": model.name, "messages": messages,
                      "max_tokens": max_tokens, "temperature": temperature})
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            r = client.post(f"{model.endpoint}/api/chat",
                json={"model": model.name, "messages": messages})
            if r.status_code == 200:
                return r.json().get("message", {}).get("content") or ""
    except Exception:
        pass
    return None


# Provider 優先順序（按成本效益）
PROVIDER_PRIORITY = ["nvidia", "groq", "xai", "gemini", "openrouter", "openai"]

# Rate Limiting
class RateLimiter:
    """簡單的速率限制器"""
    def __init__(self, rpm: int = 40):
        self.rpm = rpm
        self.requests = defaultdict(list)
        self.lock = threading.Lock()
    
    def acquire(self, provider: str = "nvidia"):
        """獲取配額，成功返回 True"""
        with self.lock:
            now = datetime.now()
            cutoff = now - timedelta(minutes=1)
            
            # 清理舊請求
            self.requests[provider] = [t for t in self.requests[provider] if t > cutoff]
            
            if len(self.requests[provider]) < self.rpm:
                self.requests[provider].append(now)
                return True
            return False
    
    def wait_if_needed(self, provider: str = "nvidia"):
        """如果需要，等待配額"""
        while not self.acquire(provider):
            time.sleep(2)  # 等待 2 秒後重試

rate_limiter = RateLimiter(rpm=40)

# ============================================================================
# Core LLM Calling
# ============================================================================

def _get_api_key(model_key: str) -> Optional[str]:
    """獲取 API key"""
    model = MODELS.get(model_key)
    if not model:
        return None
    return os.getenv(model.api_key_env) or ("dummy" if model.provider == "ollama" else None)

def _call_nvidia(prompt: str, model_key: str = "llama-3.3-70b", system: str = None,
                 temperature: float = 0.7, max_tokens: int = None,
                 thinking: bool = False, **kwargs) -> Optional[str]:
    """呼叫 NVIDIA API"""
    api_key = _get_api_key(model_key)
    if not api_key:
        logger.warning("NVIDIA_API_KEY 未設置")
        return None
    
    model = MODELS.get(model_key)
    if not model:
        model_key = "llama-3.3-70b"
        model = MODELS[model_key]
    
    max_tokens = max_tokens or model.max_tokens
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=model.endpoint, timeout=180)
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        # 構造 extra_headers
        extra_headers = {}
        if thinking and model.supports_thinking:
            extra_headers["X-Think"] = "true"
        
        response = client.chat.completions.create(
            model=model.name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_headers=extra_headers if extra_headers else None
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"NVIDIA API 失敗 ({model_key}): {e}")
        return None

def _call_xai(prompt: str, model_key: str = "grok-beta", system: str = None,
              temperature: float = 0.7, max_tokens: int = None, **kwargs) -> Optional[str]:
    """呼叫 xAI Grok API"""
    api_key = _get_api_key(model_key)
    if not api_key:
        logger.warning("XAI_API_KEY 未設置")
        return None
    
    model = MODELS.get(model_key) or MODELS["grok-beta"]
    max_tokens = max_tokens or model.max_tokens
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=model.endpoint, timeout=120)
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=model.name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"xAI API 失敗 ({model_key}): {e}")
        return None

def _call_gemini(prompt: str, model_key: str = "gemini-2.0-flash", system: str = None,
                 temperature: float = 0.7, max_tokens: int = None, **kwargs) -> Optional[str]:
    """呼叫 Google Gemini API"""
    api_key = _get_api_key(model_key)
    if not api_key:
        logger.warning("GEMINI_API_KEY 未設置")
        return None
    
    model = MODELS.get(model_key) or MODELS["gemini-2.0-flash"]
    max_tokens = max_tokens or model.max_tokens
    
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        
        response = client.models.generate_content(
            model=model.name,
            contents=full_prompt
        )
        
        return response.text
    except Exception as e:
        logger.warning(f"Gemini API 失敗 ({model_key}): {e}")
        return None

def _call_groq(prompt: str, model_key: str = "llama-3.1-70b", system: str = None,
               temperature: float = 0.7, max_tokens: int = None, **kwargs) -> Optional[str]:
    """呼叫 Groq API"""
    api_key = _get_api_key(model_key)
    if not api_key:
        logger.warning("GROQ_API_KEY 未設置")
        return None
    
    model = MODELS.get(model_key) or MODELS["llama-3.1-70b"]
    max_tokens = max_tokens or model.max_tokens
    
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=model.name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"Groq API 失敗 ({model_key}): {e}")
        return None

def _call_openai(prompt: str, model_key: str = "gpt-4o-mini", system: str = None,
                 temperature: float = 0.7, max_tokens: int = None, **kwargs) -> Optional[str]:
    """呼叫 OpenAI API"""
    api_key = _get_api_key(model_key)
    if not api_key:
        logger.warning("OPENAI_API_KEY 未設置")
        return None
    
    model = MODELS.get(model_key) or MODELS["gpt-4o-mini"]
    max_tokens = max_tokens or model.max_tokens
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, timeout=120)
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=model.name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"OpenAI API 失敗 ({model_key}): {e}")
        return None

def _call_openrouter(prompt: str, model_key: str = "openrouter-gemini", system: str = None,
                     temperature: float = 0.7, max_tokens: int = None, **kwargs) -> Optional[str]:
    """呼叫 OpenRouter API"""
    api_key = _get_api_key(model_key)
    if not api_key:
        logger.warning("OPENROUTER_API_KEY 未設置")
        return None
    
    model = MODELS.get(model_key) or MODELS["openrouter-gemini"]
    max_tokens = max_tokens or model.max_tokens
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=model.endpoint, timeout=120)
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=model.name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"OpenRouter API 失敗 ({model_key}): {e}")
        return None

# Provider → 呼叫函數映射
PROVIDER_CALLERS = {
    "nvidia": _call_nvidia,
    "xai": _call_xai,
    "gemini": _call_gemini,
    "groq": _call_groq,
    "openai": _call_openai,
    "openrouter": _call_openrouter,
    "ollama": _call_ollama,
}

# ============================================================================
# Main Interface
# ============================================================================

def call_nim(
    prompt: str,
    model: str = None,
    task_type: str = "medium",
    system: str = None,
    temperature: float = 0.7,
    max_tokens: int = None,
    max_retries: int = 3,
    thinking: bool = False,
    fallback_models: List[str] = None,
    **kwargs
) -> Optional[str]:
    """
    統一的 NIM API 呼叫介面
    
    參數:
        prompt: 用戶提示詞
        model: 直接指定模型（如 "glm-5.1", "llama-3.3-70b"），或 None 自動選擇
        task_type: 任務類型（quick/medium/deep/script/strategy/json）
        system: 系統提示詞
        temperature: 生成溫度
        max_tokens: 最大 token 數
        max_retries: 最大重試次數
        thinking: 是否啟用思考模型
        fallback_models: 備用模型列表
    
    返回:
        str: 生成的文本，或 None（所有 provider 都失敗）
    
    用法示例:
        # 自動選擇模型
        result = call_nim("分析今天市場", task_type="quick")
        
        # 指定模型
        result = call_nim("深度分析", model="glm-5.1", thinking=True)
        
        # 純文字生成
        result = call_nim("寫一個推文", model="llama-3.1-8b")
    """
    
    # 決定要嘗試的模型列表
    if model:
        # 直接指定模型
        model_list = [model]
        if fallback_models:
            model_list.extend(fallback_models)
    elif task_type:
        # 根據任務類型選擇
        base_models = TASK_MODEL_MAP.get(task_type, TASK_MODEL_MAP["medium"])
        model_list = list(base_models)
        if fallback_models:
            model_list.extend(fallback_models)
    else:
        # 預設順序
        model_list = ["llama-3.3-70b", "llama-3.1-70b", "grok-beta", "gemini-2.0-flash"]
    
    # 如果啟用思考模式，優先選擇支援的模型
    if thinking:
        thinking_models = [m for m in model_list if MODELS.get(m, ModelConfig("", "", "", "")).supports_thinking]
        if thinking_models:
            model_list = thinking_models + [m for m in model_list if m not in thinking_models]
    
    # 去除重複
    seen = set()
    unique_models = []
    for m in model_list:
        if m not in seen:
            seen.add(m)
            unique_models.append(m)
    model_list = unique_models
    
    logger.info(f"NIM API 呼叫: task_type={task_type}, models={model_list[:3]}...")
    
    # 嘗試每個模型
    for model_key in model_list:
        model_config = MODELS.get(model_key)
        if not model_config:
            logger.warning(f"未知模型: {model_key}")
            continue
        
        api_key = _get_api_key(model_key)
        if not api_key:
            logger.info(f"{model_key} API key 未設置，跳過")
            continue
        
        provider = model_config.provider
        caller = PROVIDER_CALLERS.get(provider)
        if not caller:
            logger.warning(f"未知的 provider: {provider}")
            continue
        
        # NVIDIA 需要 rate limiting
        if provider == "nvidia":
            rate_limiter.wait_if_needed(provider)
        
        # 嘗試呼叫
        for attempt in range(max_retries):
            try:
                result = caller(
                    prompt=prompt,
                    model_key=model_key,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    thinking=thinking,
                    **kwargs
                )
                
                if result:
                    logger.info(f"✓ NIM 成功: {model_key}")
                    return result
                
            except Exception as e:
                logger.warning(f"NIM {model_key} 嘗試 {attempt+1}/{max_retries} 失敗: {e}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指數退避
        
        logger.warning(f"NIM {model_key} 完全失敗，切換到下一個模型")
    
    logger.error("所有 NIM provider 都失敗")
    return None

# ============================================================================
# Specialized Functions
# ============================================================================

def optimize_script_with_nim(initial_script: str, task_type: str = "script", **kwargs) -> str:
    """
    使用 NIM API 優化 podcast 腳本
    
    向後相容於原 grok_api.optimize_script_with_grok
    """
    prompt = (
        "你是一位專業投資大師，名叫幫幫忙，請根據以下初始逐字稿，使用繁體中文撰寫一段約10分鐘的Podcast播報逐字稿，"
        "風格需更口語化、自然，適合廣播節目，控制在3000字以內。請保留所有市場數據（包括收盤價和成交金額，單位為台幣億元），"
        "並融入專業分析，確保內容符合台灣慣用語，保留英文術語（如 Nvidia、Fed）。\n\n"
        f"初始逐字稿：\n{initial_script}\n\n"
        "注意：僅輸出繁體中文逐字稿正文，勿包含任何說明或JSON格式。"
    )
    
    system = "你是一位專業財經科技主持人，擅長以口語化方式呈現財經分析。"
    
    result = call_nim(
        prompt=prompt,
        task_type=task_type,
        system=system,
        temperature=0.4,
        max_tokens=3000,
        **kwargs
    )
    
    return result if result else initial_script

def ask_nim_json(prompt: str, task_type: str = "json", **kwargs) -> Optional[Dict]:
    """
    呼叫 NIM API 並期望返回 JSON
    
    用於策略優化等需要結構化輸出的場景
    """
    result = call_nim(
        prompt=prompt,
        task_type=task_type,
        temperature=0.3,
        max_tokens=4096,
        **kwargs
    )
    
    if not result:
        return None
    
    # 嘗試解析 JSON
    try:
        # 去除 markdown 代碼塊
        text = result.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失敗: {e}")
        return None

# ============================================================================
# Task Chain (任務鏈)
# ============================================================================

class TaskChain:
    """
    任務鏈 - 將多個 LLM 任務串聯執行
    
    用法:
        result = (TaskChain()
            .then("收集數據", task_type="quick")
            .then("分析市場趨勢", task_type="medium")
            .then("生成 Podcast 腳本", task_type="script")
            .execute())
    """
    
    def __init__(self, system: str = None):
        self.tasks: List[Dict] = []
        self.system = system or "你是一個專業的AI助手，擅長分析市場和生成投資建議。"
    
    def then(self, prompt: str, task_type: str = "medium", model: str = None, 
             condition: Callable[[str], bool] = None, **kwargs) -> "TaskChain":
        """
        添加一個任務到鏈
        
        參數:
            prompt: 任務描述
            task_type: 任務類型
            model: 指定模型（可選）
            condition: 條件函數，接收上一個任務的輸出，返回 True 繼續執行
        """
        self.tasks.append({
            "prompt": prompt,
            "task_type": task_type,
            "model": model,
            "condition": condition,
            "kwargs": kwargs
        })
        return self
    
    def execute(self, stop_on_error: bool = True) -> List[Dict]:
        """
        執行任務鏈
        
        返回:
            List[Dict]: 每個任務的結果列表
        """
        results = []
        context = ""
        
        for i, task in enumerate(self.tasks):
            logger.info(f"執行任務 {i+1}/{len(self.tasks)}: {task['task_type']}")
            
            # 如果有條件，檢查是否繼續
            if task["condition"] and context:
                if not task["condition"](context):
                    logger.info(f"任務 {i+1} 條件不滿足，跳過")
                    results.append({"success": False, "skipped": True, "output": None})
                    continue
            
            # 執行任務
            full_prompt = f"{context}\n\n---\n\n{task['prompt']}" if context else task['prompt']
            
            output = call_nim(
                prompt=full_prompt,
                task_type=task["task_type"],
                model=task["model"],
                system=self.system,
                **task["kwargs"]
            )
            
            if output:
                results.append({"success": True, "output": output})
                context = output  # 將輸出傳遞給下一個任務
            else:
                logger.error(f"任務 {i+1} 失敗")
                results.append({"success": False, "output": None})
                if stop_on_error:
                    break
        
        return results

# ============================================================================
# 向後兼容接口
# ============================================================================

# 保持與原 grok_api.py 的接口相容
def optimize_script_with_grok(initial_script: str, api_key: str = None, 
                              model: str = "grok-4", max_retries: int = 3) -> str:
    """向後兼容: 使用 Grok 優化腳本（現在內部使用 NIM API）"""
    return optimize_script_with_nim(initial_script, task_type="script")

def ask_grok_json(prompt: str, role: str = "user", model: str = "grok-4") -> Optional[Dict]:
    """向後兼容: 呼叫 Grok 返回 JSON（現在內部使用 NIM API）"""
    return ask_nim_json(prompt, task_type="json")

# ============================================================================
# 工具函數
# ============================================================================

def list_available_models() -> Dict[str, Any]:
    """列出所有可用的模型及其狀態"""
    available = {}
    for key, config in MODELS.items():
        api_key = _get_api_key(key)
        available[key] = {
            "provider": config.provider,
            "model_name": config.name,
            "available": api_key is not None,
            "supports_thinking": config.supports_thinking,
            "supports_tools": config.supports_tools,
            "cost_tier": config.cost_tier,
        }
    return available

def get_best_model(task_type: str = "medium") -> Optional[str]:
    """根據任務類型獲取最佳可用模型"""
    candidates = TASK_MODEL_MAP.get(task_type, TASK_MODEL_MAP["medium"])
    for model_key in candidates:
        if _get_api_key(model_key):
            return model_key
    return None

# ============================================================================
# 測試
# ============================================================================

if __name__ == "__main__":
    print("=== NIM API 可用模型 ===")
    models = list_available_models()
    for key, info in models.items():
        status = "✓" if info["available"] else "✗"
        print(f"  {status} {key} ({info['provider']})")
    
    print("\n=== 測試 NIM API ===")
    test_result = call_nim("說一句話測試", task_type="quick")
    if test_result:
        print(f"✓ NIM API 測試成功: {test_result[:100]}...")
    else:
        print("✗ NIM API 測試失敗")