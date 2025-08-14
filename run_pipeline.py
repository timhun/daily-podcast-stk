#!/usr/bin/env python3
# run_pipeline.py

import os
import importlib.util
import sys
import traceback
from datetime import datetime

# ===== Slack 通知功能 =====
import requests

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")

def send_slack_message(message):
    """發送 Slack 訊息"""
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL:
        print("[警告] Slack 通知未啟用，請設定 SLACK_BOT_TOKEN 與 SLACK_CHANNEL")
        return
    url = "https://slack.com/api/chat.postMessage"
    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
    data = {"channel": SLACK_CHANNEL, "text": message}
    try:
        r = requests.post(url, headers=headers, data=data)
        if r.status_code != 200 or not r.json().get("ok"):
            print(f"[錯誤] Slack 發送失敗: {r.text}")
    except Exception as e:
        print(f"[錯誤] Slack 發送失敗: {e}")

# ===== Step 1: 使用 Groq LLM 生成策略 =====
def generate_strategy():
    print("[1/3] 生成交易策略...")
    result = os.system(f"{sys.executable} src/strategy_llm_groq.py")
    if result != 0:
        raise RuntimeError("Groq 策略生成失敗")
    print("[完成] 策略已生成到 strategy_candidate.py")

# ===== Step 2: 載入策略模組 =====
def load_strategy():
    print("[2/3] 載入策略模組...")
    strategy_path = os.path.abspath("strategy_candidate.py")
    spec = importlib.util.spec_from_file_location("strategy_candidate", strategy_path)
    strategy_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(strategy_module)
    print("[完成] 策略載入成功")
    return strategy_module

# ===== Step 3: 執行策略 =====
def run_strategy(strategy_module):
    print("[3/3] 執行策略回測...")
    if hasattr(strategy_module, "run"):
        result = strategy_module.run()
        print("[完成] 策略回測完成")
        return result
    else:
        raise AttributeError("策略檔案缺少 run() 函式")

# ===== 主流程 =====
if __name__ == "__main__":
    try:
        start_time = datetime.now()
        generate_strategy()
        strategy = load_strategy()
        result = run_strategy(strategy)

        msg = f"✅ 交易策略流程完成\n生成時間: {start_time}\n結果摘要: {result}"
        print(msg)
        send_slack_message(msg)

    except Exception as e:
        error_msg = f"❌ 交易策略流程失敗\n錯誤: {e}\n{traceback.format_exc()}"
        print(error_msg)
        send_slack_message(error_msg)
        sys.exit(1)
