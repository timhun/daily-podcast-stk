import requests

try:
    resp = requests.get("https://api.thenewsapi.com/v1/news/all?api_token=demo&language=zh&categories=business")
    news = resp.json()["data"][0]["title"] + "\n" + resp.json()["data"][0]["description"]
except Exception:
    news = "美國通膨降溫、聯準會利率維持不變，市場觀望。"

with open("podcast/latest/news_macro.txt", "w") as f:
    f.write(news)