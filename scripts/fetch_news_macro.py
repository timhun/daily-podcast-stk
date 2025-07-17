import os
import requests
from bs4 import BeautifulSoup

os.makedirs('podcast/latest', exist_ok=True)

try:
    r = requests.get("https://www.bing.com/news/search?q=美國+經濟", timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    article = soup.find("a", {"class": "title"})
    title = article.text.strip() if article else "找不到最新總經新聞"
except Exception:
    title = "總經新聞服務異常，請明天再試"
with open('podcast/latest/news_macro.txt', 'w') as f:
    f.write(title)