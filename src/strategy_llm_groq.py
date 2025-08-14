#!/usr/bin/env python3
# src/strategy_llm_groq.py
import os
import json
import datetime
from groq import Groq

OUTPUT_FILE = "strategy_generated.json"

def generate_strategy_with_groq():
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    prompt = """
你是一位專業的量化交易策略顧問，請根據目前的市場情況，輸出一個新的短期交易策略。
要求：
1. 使用 Python + pandas + ta 庫撰寫
2. 僅輸出策略邏輯（函式）
3. 適用台股（0050.TW）與美股（QQQ）
4. 同時輸出 200 字以內的策略摘要
輸出格式：
策略名稱、策略摘要、策略程式碼
"""

    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1500
    )

    content = response.choices[0].message["content"].strip()

    # 簡單解析 LLM 輸出
    strategy_name = "Groq_LLM_Strategy_" + datetime.datetime.now().strftime("%Y%m%d")
    strategy_summary = ""
    strategy_code = ""

    if "策略摘要" in content:
        parts = content.split("策略摘要")
        if len(parts) > 1:
            summary_part = parts[1].strip()
            if "策略程式碼" in summary_part:
                strategy_summary, code_part = summary_part.split("策略程式碼", 1)
                strategy_code = code_part.strip()
            else:
                strategy_summary = summary_part
    else:
        strategy_summary = "LLM 自動生成的交易策略"
        strategy_code = content

    # 標準化 JSON 輸出
    output_data = {
        "name": strategy_name,
        "generated_at": datetime.datetime.now().isoformat(),
        "summary": strategy_summary.strip(),
        "code": strategy_code.strip()
    }

    # 儲存 JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"[INFO] 策略已生成並儲存至 {OUTPUT_FILE}")
    return output_data


if __name__ == "__main__":
    generate_strategy_with_groq()
