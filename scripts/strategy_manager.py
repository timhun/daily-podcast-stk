# scripts/strategy_manager.py
import pandas as pd
import json
import os
import logging
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from openai import OpenAI  # 兼容Grok API
from datetime import datetime
import pytz
import numpy as np

logging.basicConfig(filename='logs/strategy_manager.log', level=logging.INFO, format='%(asctime)s - %(message)s')

class LSTMDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)
    
    def __len__(self):
        return len(self.y)
    
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

class LSTMModel(nn.Module):
    def __init__(self, input_size, hidden_size):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x):
        _, (h, _) = self.lstm(x)
        out = self.fc(h.squeeze(0))
        return self.sigmoid(out)

def optimize_params_with_grok(strategy_name, current_params, performance):
    client = OpenAI(base_url="https://api.x.ai/v1", api_key=os.environ['GROK_API_KEY'])
    prompt = f"Optimize parameters for {strategy_name} based on performance: {performance}. Current params: {current_params}. Suggest improved params."
    response = client.chat.completions.create(
        model="grok-3-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content  # Parse to dict in production

def main(symbol=None):
    with open('config.json', 'r') as f:
        config = json.load(f)
    with open('strategies.json', 'r') as f:
        strategies = json.load(f)['strategies']
    
    focus_symbols = ['0050TW', 'QQQ']  # Cleaned for file
    if symbol:
        focus_symbols = [symbol.replace('.', '').replace('^', '')]
    
    for sym in focus_symbols:
        daily_file = f"data/daily_{sym}.csv"
        if not os.path.exists(daily_file):
            logging.error(f"Data file missing for {sym}")
            continue
        
        df = pd.read_csv(daily_file, index_col='Date', parse_dates=True)
        df['Return'] = df['Close'].pct_change()
        df['Label'] = np.where(df['Return'] > 0, 1, 0)  # Baseline: up/down
        df.dropna(inplace=True)
        
        baseline_acc = max(df['Label'].mean(), 1 - df['Label'].mean())  # Baseline win rate
        
        best_strategy = None
        best_win_rate = 0
        best_params = {}
        
        for strat in strategies:
            if strat['name'] == 'RandomForest':
                X = df[['Open', 'High', 'Low', 'Volume']].values
                y = df['Label'].values
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
                model = RandomForestClassifier(**strat['params'])
                model.fit(X_train, y_train)
                preds = model.predict(X_test)
                acc = accuracy_score(y_test, preds)
            
            elif strat['name'] == 'LSTM':
                seq_len = 10
                X = []
                y = []
                for i in range(len(df) - seq_len):
                    X.append(df[['Open', 'High', 'Low', 'Close', 'Volume']].iloc[i:i+seq_len].values)
                    y.append(df['Label'].iloc[i+seq_len])
                X = np.array(X)
                y = np.array(y)
                train_size = int(0.8 * len(X))
                X_train, X_test = X[:train_size], X[train_size:]
                y_train, y_test = y[:train_size], y[train_size:]
                
                dataset_train = LSTMDataset(X_train, y_train)
                loader = DataLoader(dataset_train, batch_size=strat['params']['batch_size'])
                
                model = LSTMModel(input_size=5, hidden_size=strat['params']['units'])
                criterion = nn.BCELoss()
                optimizer = torch.optim.Adam(model.parameters())
                
                for epoch in range(strat['params']['epochs']):
                    for batch_x, batch_y in loader:
                        optimizer.zero_grad()
                        out = model(batch_x)
                        loss = criterion(out.squeeze(), batch_y)
                        loss.backward()
                        optimizer.step()
                
                with torch.no_grad():
                    preds = model(torch.tensor(X_test, dtype=torch.float32)).squeeze().numpy() > 0.5
                    acc = accuracy_score(y_test, preds.astype(int))
            
            logging.info(f"{strat['name']} for {sym}: Win rate {acc}")
            
            if acc > baseline_acc and acc > best_win_rate:
                best_win_rate = acc
                best_strategy = strat['name']
                best_params = strat['params']
        
        if best_strategy:
            # Optimize with Grok API
            perf = f"Win rate: {best_win_rate}"
            optimized = optimize_params_with_grok(best_strategy, best_params, perf)
            logging.info(f"Grok optimized: {optimized}")
            # Parse optimized to dict, here assume same
            output = {"strategy": best_strategy, "params": best_params, "win_rate": best_win_rate}
            json_file = f"data/strategy_best_{sym}.json"
            with open(json_file, 'w') as f:
                json.dump(output, f)
            logging.info(f"Best strategy for {sym}: {output}")

if __name__ == "__main__":
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else None
    main(symbol)
