# scripts/fetch_ai_topic.py
import os
import datetime
from utils_podcast import get_podcast_mode, TW_TZ
from generate_script_grok import generate_script_from_grok
from generate_script_openrouter import generate_script_from_openrouter

def get_ai_topic_text(mode: str = "us") -> str:
    now = datetime.datetime.now(TW_TZ)
    date_str = now.strftime("%Y年%m月%d日")

    # 讀取 prompt 檔
    prompt_file = f"prompt/ai_topic-{mode}.txt"
    if not os.path.exists(prompt_file):
        print(f"⚠️ 找不到 AI 主題 prompt：{prompt_file}")
        return ""

    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # 填入 prompt
    prompt = prompt_template.format(date=date_str)

    # 使用 Grok → OpenRouter fallback
    try:
        print("🧠 使用 Grok 產生 AI 主題...")
        result = generate_script_from_grok(prompt)
        if result:
            print("✅ 成功產出 AI 主題（Grok）")
            return result.strip()
        raise Exception("Grok 回傳為空")
    except Exception as e:
        print(f"⚠️ Grok 失敗：{e}")
        try:
            print("📡 使用 OpenRouter 產出 AI 主題...")
            result = generate_script_from_openrouter(prompt)
            if result:
                print("✅ 成功產出 AI 主題（OpenRouter）")
                return result.strip()
        except Exception as e2:
            print(f"❌ OpenRouter 也失敗：{e2}")
            return ""

# CLI 測試模式
if __name__ == "__main__":
    mode = get_podcast_mode()
    ai_text = get_ai_topic_text(mode)
    if ai_text:
        print(f"\n🎯 AI 主題產出：\n{ai_text}")
    else:
        print("⚠️ 無法產出 AI 主題")
