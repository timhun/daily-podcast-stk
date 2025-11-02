import os
import pandas as pd
import matplotlib.pyplot as plt
import itertools
from loguru import logger
from cloud_manager import upload_chart

def generate_performance_chart(df, symbol, timeframe):
    """Generates a performance chart, uploads it, and returns the URL."""
    save_path = f"data/strategy/performance/{symbol}_{timeframe}_performance.png"
    try:
        plt.figure(figsize=(10, 6))
        # Ensure the index is a datetime object for plotting
        if not pd.api.types.is_datetime64_any_dtype(df.index):
            # Assuming the index is date strings, convert it
            df.index = pd.to_datetime(df.index)

        plt.plot(df.index, df['strategy_returns'].cumsum(), label='Strategy Returns')
        plt.title(f"{symbol} {timeframe} Strategy Performance")
        plt.xlabel('Date')
        plt.ylabel('Cumulative Returns')
        plt.legend()
        plt.grid()
        
        output_dir = os.path.dirname(save_path)
        os.makedirs(output_dir, exist_ok=True)
        
        plt.savefig(save_path)
        plt.close()
        logger.info(f"Generated performance chart for {symbol} {timeframe} at {save_path}")

        # Upload the chart and get the URL
        chart_url = upload_chart(save_path)
        logger.info(f"Uploaded chart for {symbol} to {chart_url}")
        return chart_url

    except Exception as e:
        logger.error(f"Failed to generate or upload performance chart for {symbol}: {str(e)}")
        return None

def get_param_combinations(params):
    keys = params.keys()
    values = [params[key] if isinstance(params[key], list) else [params[key]] for key in keys]
    combinations = [dict(zip(keys, combo)) for combo in itertools.product(*values)]
    return combinations
