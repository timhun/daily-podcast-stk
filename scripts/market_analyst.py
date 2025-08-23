#market_analyst.py
import pandas as pd
import json
import os
import sys
from utils import setup_json_logger, slack_alert
import numpy as np

logger = setup_json_logger('market_analyst')

def calculate_macd(df):
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def calculate_rsi(df, periods=14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def main(mode=None):
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    focus_symbol = 'QQQ' if mode == 'us' else '0050.TW'
    clean_symbol = focus_symbol.replace('.', '').replace('^', '')
    
    daily_file = f"data/daily_{clean_symbol}.csv"
    strategy_file = f"data/strategy_best_{clean_symbol}.json"
    
    if not os.path.exists(daily_file) or not os.path.exists(strategy_file):
        slack_alert(f"Missing files for {focus_symbol}")
        return
    
    df = pd.read_csv(daily_file, index_col='Date', parse_dates=True)
    with open(strategy_file, 'r') as f:
        strategy = json.load(f)
    
    df['MACD'], df['Signal'] = calculate_macd(df)
    df['RSI'] = calculate_rsi(df)
    
    latest = df.iloc[-1]
    trend = "up" if latest['Close'] > df['Close'].mean() else "down"
    signal_buy = latest['MACD'] > latest['Signal'] and latest['RSI'] < 70
    signal_sell = latest['MACD'] < latest['Signal'] or latest['RSI'] > 70
    
    volatility = df['Close'].pct_change().std() * np.sqrt(252)
    
    suggestion = "Buy" if signal_buy and strategy['win_rate'] > 0.55 else "Sell" if signal_sell else "Hold"
    position = "Increase" if trend == "up" and suggestion == "Buy" else "Reduce" if trend == "down" else "Neutral"
    
    output = {
        "trend": trend,
        "suggestion": suggestion,
        "position_adjust": position,
        "risk": f"Volatility: {volatility:.2%}",
        "indicators": {"MACD": latest['MACD'], "Signal": latest['Signal'], "RSI": latest['RSI']}
    }
    
    json_file = f"data/market_analysis_{clean_symbol}.json"
    with open(json_file, 'w') as f:
        json.dump(output, f)
    logger.info(json.dumps({"symbol": focus_symbol, "output": output}))

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ['us', 'tw'] else None
    main(mode)
