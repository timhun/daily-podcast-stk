import random

quotes = [
    "投資不是賺錢的藝術，而是避險的科學。",
    "市場短期是投票機，長期是計算機。",
    "控制風險永遠比追求報酬更重要。",
    "你永遠賺不到自己認知以外的錢。"
]
with open("podcast/latest/quote.txt", "w") as f:
    f.write(random.choice(quotes))