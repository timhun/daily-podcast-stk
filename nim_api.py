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
import re
from typing import Optional, Dict, List, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import threading

# Load .env file for API keys
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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
    "nemotron-3-super-120b-a12b": ModelConfig(
        name="nvidia/nemotron-3-super-120b-a12b",
        provider="nvidia",
        endpoint="https://integrate.api.nvidia.com/v1",
        api_key_env="NVIDIA_API_KEY",
        max_tokens=8192,
        supports_tools=True,
        cost_tier=1,
        latency_tier=2
    ),
    "glm-5.2": ModelConfig(
        name="z-ai/glm-5.2",
        provider="nvidia",
        endpoint="https://integrate.api.nvidia.com/v1",
        api_key_env="NVIDIA_API_KEY",
        max_tokens=8192,
        supports_thinking=True,
        cost_tier=1,
        latency_tier=3
    ),
    "minimax-m3": ModelConfig(
        name="minimaxai/minimax-m3",
        provider="nvidia",
        endpoint="https://integrate.api.nvidia.com/v1",
        api_key_env="NVIDIA_API_KEY",
        max_tokens=8192,
        supports_thinking=True,
        cost_tier=1,
        latency_tier=2
    ),
    "qwen-3.6": ModelConfig(
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
    "gemini-3.6-flash": ModelConfig(
        name="gemini-3.6-flash",
        provider="gemini",
        endpoint="https://generativelanguage.googleapis.com",
        api_key_env="GEMINI_API_KEY",
        max_tokens=8192,
        cost_tier=1,
        latency_tier=1
    ),
    "gemini-3.1-pro": ModelConfig(
        name="gemini-3.1-pro",
        provider="gemini",
        endpoint="https://generativelanguage.googleapis.com",
        api_key_env="GEMINI_API_KEY",
        max_tokens=8192,
        cost_tier=1,
        latency_tier=2
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
        name="google/gemini-flash-latest:free",
        provider="openrouter",
        endpoint="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        max_tokens=4096,
        cost_tier=1,
        latency_tier=1
    ),
    
    # Local Ollama (fallback)
    "qwen3.6-ollama": ModelConfig(
        name="qwen3.6:latest",
        provider="ollama",
        endpoint="http://localhost:11434",
        api_key_env="",
        max_tokens=8192,
        cost_tier=0,
        latency_tier=3
    ),
}

# 任務類型 → 推薦模型 (優先使用 Gemini)
TASK_MODEL_MAP = {
    "quick": ["gemini-3.6-flash", "gemini-3.6-flash", "gemini-3.6-flash", "llama-3.1-8b", "qwen-3.6", "grok-beta", "qwen3.6-ollama"],
    "medium": ["gemini-3.6-flash", "gemini-3.6-flash", "gemini-3.6-flash", "llama-3.1-70b", "deepseek-v3.2"],
    "deep": ["gemini-3.6-flash", "gemini-3.6-flash", "gemini-3.6-flash", "glm-5.1", "deepseek-v3.2"],
    "script": ["gemini-3.6-flash", "gemini-3.6-flash", "gemini-3.6-flash", "llama-3.1-70b", "glm-5.1"],  # Podcast 腳本生成
    "strategy": ["gemini-3.6-flash", "gemini-3.6-flash", "gemini-3.6-flash", "glm-5.1", "deepseek-v3.2"],  # 策略分析
    "json": ["gemini-3.6-flash", "gemini-3.6-flash", "gemini-3.6-flash", "llama-3.1-70b", "qwen-3.6"],  # JSON 輸出
}


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """簡單的 RPM 速率限制器"""
    
    def __init__(self, rpm: int = 40):
        self.rpm = rpm
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
        self.lock = threading.Lock()
    
    def acquire(self, provider: str = "nvidia") -> bool:
        """獲取配額，成功返回 True"""
        with self.lock:
            now = datetime.now()
            # 清理過期請求
            self.requests[provider] = [
                req_time for req_time in self.requests[provider]
                if now - req_time < timedelta(minutes=1)
            ]
            if len(self.requests[provider]) < self.rpm:
                self.requests[provider].append(now)
                return True
            return False
    
    def wait_if_needed(self, provider: str = "nvidia"):
        """等待直到有配額"""
        while not self.acquire(provider):
            time.sleep(1.5)  # 等待 1.5 秒後重試

rate_limiter = RateLimiter(40)


# ============================================================================
# API Key 管理
# ============================================================================

def _get_api_key(model_key: str) -> Optional[str]:
    """獲取模型對應的 API Key"""
    model_config = MODELS.get(model_key)
    if not model_config:
        return None
    return os.getenv(model_config.api_key_env)


# ============================================================================
# Provider 呼叫器
# ============================================================================

def _call_nvidia(prompt, model_config, system=None, temperature=0.7, max_tokens=None, **kwargs):
    """呼叫 NVIDIA NIM API"""
    import httpx
    
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    api_key = os.getenv(model_config.api_key_env)
    if not api_key:
        logger.warning(f"{model_config.api_key_env} 未設置")
        return None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_config.name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens or model_config.max_tokens,
    }
    
    try:
        with httpx.Client(timeout=180) as client:
            response = client.post(
                f"{model_config.endpoint}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"NVIDIA API 呼叫失敗: {e}")
        return None


def _call_gemini(prompt, model_config, system=None, temperature=0.7, max_tokens=None, **kwargs):
    """呼叫 Google Gemini API"""
    import httpx
    
    api_key = os.getenv(model_config.api_key_env)
    if not api_key:
        logger.warning("GEMINI_API_KEY 未設置")
        return None
    
    # Gemini API 格式
    parts = []
    if system:
        parts.append({"text": f"System: {system}"})
    parts.append({"text": prompt})
    
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens or model_config.max_tokens,
        }
    }
    
    try:
        with httpx.Client(timeout=180) as client:
            url = f"{model_config.endpoint}/v1beta/models/{model_config.name}:generateContent?key={api_key}"
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Gemini API 呼叫失敗: {e}")
        return None


def _call_openai_compatible(prompt, model_config, system=None, temperature=0.7, max_tokens=None, **kwargs):
    """呼叫 OpenAI 兼容 API (Groq, xAI, OpenAI, OpenRouter)"""
    import httpx
    
    api_key = os.getenv(model_config.api_key_env)
    if not api_key:
        logger.warning(f"{model_config.api_key_env} 未設置")
        return None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": model_config.name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens or model_config.max_tokens,
    }
    
    try:
        with httpx.Client(timeout=180) as client:
            response = client.post(
                f"{model_config.endpoint}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"{model_config.provider} API 呼叫失敗: {e}")
        return None


def _call_ollama(prompt, model_config, system=None, temperature=0.7, max_tokens=None, **kwargs):
    """呼叫 Ollama 本地 API"""
    import httpx
    
    # Ollama 不需要 API key
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": model_config.name,
        "messages": messages,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens or model_config.max_tokens,
        },
        "stream": False
    }
    
    try:
        with httpx.Client(timeout=180) as client:
            response = client.post(
                f"{model_config.endpoint}/api/chat",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
    except Exception as e:
        logger.error(f"Ollama API 呼叫失敗: {e}")
        return None


PROVIDER_CALLERS = {
    "nvidia": _call_nvidia,
    "gemini": _call_gemini,
    "xai": _call_openai_compatible,
    "groq": _call_openai_compatible,
    "openai": _call_openai_compatible,
    "openrouter": _call_openai_compatible,
    "ollama": _call_ollama,
}


# ============================================================================
# Core LLM Calling
# ============================================================================

def call_nim(
    prompt: str,
    task_type: str = "medium",
    model: str = None,
    system: str = None,
    temperature: float = 0.7,
    max_tokens: int = None,
    thinking: bool = False,
    **kwargs
) -> Optional[str]:
    """
    統一 LLM 呼叫介面
    
    參數:
        prompt: 輸入提示詞
        task_type: 任務類型 ("quick", "medium", "deep", "script", "strategy", "json")
        model: 指定模型 key (可選，不指定則自動選擇)
        system: 系統提示詞
        temperature: 溫度
        max_tokens: 最大 token 數
        thinking: 是否啟用思考模式
        
    返回:
        生成的文本，失敗返回 None
    """
    
    # 選擇模型
    if model is None:
        model = get_best_model(task_type)
        if not model:
            logger.error(f"找不到可用模型: {task_type}")
            return None
    
    model_config = MODELS.get(model)
    if not model_config:
        logger.error(f"未知模型: {model}")
        return None
    
    # 檢查 API Key
    api_key = _get_api_key(model)
    if api_key is None and model_config.provider != "ollama":
        logger.warning(f"{model} 的 API Key 未設置 ({model_config.api_key_env})")
        # 嘗試降級
        model = get_best_model(task_type)
        if not model:
            return None
        model_config = MODELS[model]
        api_key = _get_api_key(model)
    
    # 速率限制
    if model_config.provider == "nvidia":
        rate_limiter.wait_if_needed("nvidia")
    
    # 呼叫對應的 provider
    caller = PROVIDER_CALLERS.get(model_config.provider)
    if not caller:
        logger.error(f"不支援的 provider: {model_config.provider}")
        return None
    
    logger.info(f"NIM API 呼叫: task_type={task_type}, model={model} ({model_config.provider})")
    
    result = caller(
        prompt=prompt,
        model_config=model_config,
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )
    
    if result:
        logger.info(f"NIM API 成功: {len(result)} 字元")
    else:
        logger.warning(f"NIM API 失敗: {model}")
    
    return result


# ============================================================================
# JSON 專用介面
# ============================================================================

def ask_nim_json(
    prompt: str,
    task_type: str = "json",
    model: str = None,
    system: str = None,
    **kwargs
) -> Optional[Dict]:
    """呼叫 NIM API 並解析 JSON 回應"""
    result = call_nim(
        prompt=prompt,
        task_type=task_type,
        model=model,
        system=system,
        temperature=0.1,  # JSON 任務用低溫度
        **kwargs
    )
    
    if not result:
        return None
    
    # 嘗試解析 JSON
    try:
        # 先找代碼塊裡的 JSON
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        # 再找第一個 { 到最後一個 }
        json_match = re.search(r'(\{.*\})', result, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
    except Exception as e:
        logger.error(f"JSON 解析失敗: {e}")
    return None


def optimize_script_with_nim(initial_script: str, task_type: str = "script") -> str:
    """優化腳本（向後兼容）"""
    return call_nim(
        prompt=f"優化以下投資播客腳本，使其更專業、流暢、有說服力：\n\n{initial_script}",
        task_type=task_type,
    )


# ============================================================================
# 任務鏈
# ============================================================================

class TaskChain:
    """任務鏈 - 依序執行多個任務，前一個輸出作為下一個輸入"""
    
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

def ask_nim_json_legacy(prompt: str, task_type: str = "json", model: str = None, system: str = None, **kwargs):
    """呼叫 NIM API 返回 JSON（向後兼容）"""
    return ask_nim_json(prompt, task_type, model, system, **kwargs)


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
