#!/usr/bin/env python3
# src/strategy_llm_groq.py
import os
import json
import datetime
from pathlib import Path
from groq import Groq

# 預設模型與溝通設定
DEFAULT_MODEL = "llama3-70b-8192"


def generate_strategy(
    prompt: str,
    target_return: float = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7
):
    """
    使用 Groq LLM 生成交易策略
    參數:
        prompt: 基本提示詞
        target_return: (選填) 目標年化報酬率，會加入到提示中
        model: 模型名稱
        temperature: 溫度
    回傳:
        dict 格式策略
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("請設定 GROQ_API_KEY 環境變數")

    client = Groq(api_key=api_key)

    # 拼接提示詞
    if target_return is not None:
        full_prompt = f"{prompt}\n\n目標年化報酬率: {target_return:.2f}%"
    else:
        full_prompt = prompt

    # 發送請求
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": full_prompt}],
        temperature=temperature,
    )

    # 嘗試解析 JSON
    content = response.choices[0].message["content"]
    try:
        strategy = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("Groq 回應不是有效的 JSON:\n" + content)

    return strategy


def save_strategy(strategy: dict, name_prefix: str = "strategy"):
    """
    儲存策略為 JSON 檔案
    """
    Path("strategies").mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(f"strategies/{name_prefix}_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(strategy, f, ensure_ascii=False, indent=2)
    return path


if __name__ == "__main__":
    # 範例測試
    base_prompt = "請生成一個適用於台股的波段交易策略，輸出 JSON 格式"
    strat = generate_strategy(prompt=base_prompt, target_return=15.0)
    path = save_strategy(strat, name_prefix="demo")
    print(f"策略已儲存到 {path}")
