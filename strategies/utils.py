import os  # 新增匯入
import pandas as pd
import matplotlib.pyplot as plt
import itertools
from loguru import logger

def generate_performance_chart(df, symbol, timeframe):
    try:
        plt.figure(figsize=(10, 6))
        plt.plot(df['date'], df['strategy_returns'].cumsum(), label='Strategy Returns')
        plt.title(f"{symbol} {timeframe} Strategy Performance")
        plt.xlabel('Date')
        plt.ylabel('Cumulative Returns')
        plt.legend()
        plt.grid()
        output_dir = 'data/strategy/performance'
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(f"{output_dir}/{symbol}_{timeframe}_performance.png")
        plt.close()
        logger.info(f"Generated performance chart for {symbol} {timeframe}")
    except Exception as e:
        logger.error(f"Failed to generate performance chart for {symbol}: {str(e)}")

def get_param_combinations(params):
    keys = params.keys()
    values = [params[key] if isinstance(params[key], list) else [params[key]] for key in keys]
    combinations = [dict(zip(keys, combo)) for combo in itertools.product(*values)]
    return combinations
