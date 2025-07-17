import requests

# 這裡用簡單網路新聞 API，可自由換來源
try:
    resp = requests.get("https://api.thenewsapi.com/v1/news/all?api_token=demo&language=zh&categories=technology")
    news = resp.json()["data"][0]["title"] + "\n" + resp.json()["data"][0]["description"]
except Exception:
    news = "ChatGPT 4o、Grok等AI工具正在改變產業，生成式AI加速普及。"

with open("podcast/latest/news_ai.txt", "w") as f:
    f.write(news)