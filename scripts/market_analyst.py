import pandas as pd
import json
import os
import logging
import numpy as np
from datetime import datetime
import pytz

logging.basicConfig(filename='logs/market_analyst.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def calculate_macd(df):
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def main(symbol=None):
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    focus_symbols = ['0050TW', 'QQQ']
    if symbol:
        focus_symbols = [symbol.replace('.', '').replace('^', '')]
    
    for sym in focus_symbols:
        daily_file = f"data/daily_{sym}.csv"
        strategy_file = f"data/strategy_best_{sym}.json"
        
        if not os.path.exists(daily_file) or not os.path.exists(strategy_file):
            logging.error(f"Missing files for {sym}")
            continue
        
        df = pd.read_csv(daily_file, index_col='Date', parse_dates=True)
        with open(strategy_file, 'r') as f:
            strategy = json.load(f)
        
        # Indicators
        macd, signal = calculate_macd(df)
        df['MACD'] = macd
        df['Signal'] = signal
        
        latest = df.iloc[-1]
        trend = "up" if latest['Close'] > df['Close'].mean() else "down"
        signal_buy = latest['MACD'] > latest['Signal']  # Simple crossover
        
        # Risk assessment (volatility)
        volatility = df['Close'].pct_change().std() * np.sqrt(252)  # Annualized
        
        # Suggestion based on strategy
        if strategy['win_rate'] > 0.5:
            suggestion = "Buy" if signal_buy else "Sell"
            position = "Increase" if trend == "up" else "Reduce"
        else:
            suggestion = "Hold"
            position = "Neutral"
        
        output = {
            "trend": trend,
            "suggestion": suggestion,
            "position_adjust": position,
            "risk": f"Volatility: {volatility:.2%}",
            "indicators": {"MACD": latest['MACD'], "Signal": latest['Signal']}
        }
        
        json_file = f"data/market_analysis_{sym}.json"
        with open(json_file, 'w') as f:
            json.dump(output, f)
        logging.info(f"Analysis for {sym}: {output}")

if __name__ == "__main__":
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else None
    main(symbol)
