# src/strategy_llm_groq.py
import os
import json
from datetime import datetime
from groq import Groq

# ===== 基本設定 =====
OUTPUT_FILE = "strategy_candidate.py"  # 生成的策略檔案
MODEL = "mixtral-8x7b-32768"            # Groq 模型名稱，可依需求改
PROMPT_FILE = "prompts/strategy_prompt.txt"  # 策略生成提示詞檔

# 從環境變數讀取 API Key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("請先設定環境變數 GROQ_API_KEY")

# 初始化 Groq API
client = Groq(api_key=GROQ_API_KEY)


def load_prompt():
    """讀取策略提示詞"""
    if not os.path.exists(PROMPT_FILE):
        raise FileNotFoundError(f"找不到提示詞檔案: {PROMPT_FILE}")
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def generate_strategy_code(prompt):
    """使用 Groq LLM 生成策略程式碼"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "你是一位專業量化交易策略工程師，會輸出完整可執行的 Python 策略程式碼。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=4000
    )
    # 取出 LLM 回覆的內容
    return response.choices[0].message.content.strip()


def save_strategy(code):
    """儲存策略檔案"""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# 自動生成的策略檔案\n")
        f.write(f"# 生成時間: {datetime.now()}\n\n")
        f.write(code)
    print(f"[完成] 策略檔案已儲存到 {OUTPUT_FILE}")


def main():
    print("[1/3] 載入提示詞...")
    prompt = load_prompt()

    print("[2/3] 呼叫 Groq LLM 生成策略...")
    code = generate_strategy_code(prompt)

    print("[3/3] 儲存策略檔案...")
    save_strategy(code)


if __name__ == "__main__":
    main()
