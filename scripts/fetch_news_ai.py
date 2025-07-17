import os
import requests
from bs4 import BeautifulSoup

os.makedirs('podcast/latest', exist_ok=True)

try:
    r = requests.get("https://www.bing.com/news/search?q=AI", timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    article = soup.find("a", {"class": "title"})
    title = article.text.strip() if article else "找不到最新AI新聞"
except Exception:
    title = "AI新聞服務異常，請明天再試"
with open('podcast/latest/news_ai.txt', 'w') as f:
    f.write(title)