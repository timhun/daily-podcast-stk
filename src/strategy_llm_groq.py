#!/usr/bin/env python3
# src/strategy_llm_groq.py
import os
import json
from groq import Groq

# 初始化 Groq API
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def generate_strategy_llm(market_data, history_file=None, target_return=0.02):
    """
    使用 Groq LLM 根據市場資料生成策略
    :param market_data: dict/list/pd.DataFrame 形式的市場資料
    :param history_file: 過往策略檔案（可選）
    :param target_return: 目標報酬率（float, 預設 0.02 即 2%）
    """
    # 嘗試載入過往策略
    history_content = ""
    if history_file and os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history_content = f.read()
        except Exception as e:
            print(f"[WARN] 無法讀取歷史策略檔: {e}")

    # 確保 market_data 可序列化
    try:
        if not isinstance(market_data, str):
            market_data_str = json.dumps(market_data, ensure_ascii=False)
        else:
            market_data_str = market_data
    except Exception as e:
        print(f"[ERROR] 無法轉換 market_data: {e}")
        market_data_str = str(market_data)

    # 建立 prompt
    prompt = f"""
你是一位專業的量化交易策略生成器。
目標報酬率: {target_return*100:.2f}%
以下是最新市場資料：
{market_data_str}

過往策略參考：
{history_content}

請輸出 JSON 格式策略，例如：
{{
    "name": "均線突破策略",
    "entry": "...進場條件描述...",
    "exit": "...出場條件描述...",
    "stop_loss": "...停損條件...",
    "take_profit": "...停利條件..."
}}
    """

    # 呼叫 Groq API
    try:
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "你是專業的量化交易策略設計師，請輸出有效 JSON 格式。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1024
        )

        # 擷取回應
        content = completion.choices[0].message.content.strip()

        # 嘗試解析 JSON
        try:
            strategy = json.loads(content)
        except json.JSONDecodeError:
            print("[WARN] 模型輸出非 JSON，將內容包裝成 {raw_output:...}")
            strategy = {"raw_output": content}

        return strategy

    except Exception as e:
        print(f"[ERROR] Groq API 呼叫失敗: {e}")
        return {"error": str(e)}
