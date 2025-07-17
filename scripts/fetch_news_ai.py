import os
os.makedirs('podcast/latest', exist_ok=True)

ai_news = "最新AI新聞：OpenAI與xAI競爭加劇，AI工具加速滲透各行各業。"
with open('podcast/latest/news_ai.txt', 'w') as f:
    f.write(ai_news)
print("✅ [MOCK] AI新聞已產生")