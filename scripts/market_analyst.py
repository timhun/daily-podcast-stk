#market_analyst.py
import pandas as pd
import json
import os
import sys
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from statsmodels.tsa.arima.model import ARIMA
from utils import setup_json_logger, get_grok_client, slack_alert
import numpy as np
from sklearn.metrics import accuracy_score

logger = setup_json_logger('strategy_manager')

def optimize_params(strategy_name, params, performance):
    client = get_grok_client()
    prompt = f"Optimize params for {strategy_name} for short-term trading (1-3 days). Performance: {performance}. Current: {params}."
    response = client.chat.completions.create(model="grok-4-mini", messages=[{"role": "user", "content": prompt}])
    return json.loads(response.choices[0].message.content)  # Assume JSON response

def main(mode=None):
    with open('config.json', 'r') as f:
        config = json.load(f)
    with open('strategies.json', 'r') as f:
        strategies = json.load(f)
    
    focus_symbol = 'QQQ' if mode == 'us' else '0050.TW'
    clean_symbol = focus_symbol.replace('.', '').replace('^', '')
    
    daily_file = f"data/daily_{clean_symbol}.csv"
    if not os.path.exists(daily_file):
        slack_alert(f"Missing data for {focus_symbol}")
        return
    
    df = pd.read_csv(daily_file, index_col='Date', parse_dates=True)
    df['Return'] = df['Close'].pct_change()
    df['Label'] = np.where(df['Return'] > 0, 1, 0)
    df.dropna(inplace=True)
    
    # ARIMA baseline
    arima_model = ARIMA(df['Close'], order=(1,1,1)).fit()
    arima_preds = (arima_model.predict(start=len(df)-len(df)//5, end=len(df)-1) > df['Close'].shift(1)).astype(int)
    baseline_acc = accuracy_score(df['Label'][-len(arima_preds):], arima_preds)
    
    best_strategy = None
    best_win_rate = 0
    best_params = {}
    
    for strat in strategies['strategies']:
        if strat['name'] in ['RandomForest', 'XGBoost']:
            X = df[['Open', 'High', 'Low', 'Volume']].values[:-1]
            y = df['Label'].values[1:]
            model = RandomForestClassifier(**strat['params']) if strat['name'] == 'RandomForest' else XGBClassifier(**strat['params'])
            model.fit(X[:int(0.8*len(X))], y[:int(0.8*len(X))])
            preds = model.predict(X[int(0.8*len(X)):])
            acc = accuracy_score(y[int(0.8*len(X)):], preds)
        
        # Add LSTM (similar to previous)
        
        logger.info(json.dumps({"symbol": focus_symbol, "strategy": strat['name'], "win_rate": acc}))
        if acc > baseline_acc + 0.05 and acc > best_win_rate:
            best_win_rate = acc
            best_strategy = strat['name']
            best_params = strat['params']
    
    if best_strategy and best_win_rate > 0.55:
        optimized = optimize_params(best_strategy, best_params, f"Win rate: {best_win_rate}")
        output = {"strategy": best_strategy, "params": optimized, "win_rate": best_win_rate, "baseline": baseline_acc}
        json_file = f"data/strategy_best_{clean_symbol}.json"
        with open(json_file, 'w') as f:
            json.dump(output, f)
        logger.info(json.dumps({"symbol": focus_symbol, "output": output}))
    else:
        slack_alert(f"No strategy for {focus_symbol} exceeds threshold (win_rate: {best_win_rate})")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ['us', 'tw'] else None
    main(mode)
