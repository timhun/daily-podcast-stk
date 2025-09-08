import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def calculate_ma(prices, window):
    return prices.rolling(window=window).mean()

def is_bullish(ma_short, ma_mid, ma_long):
    return (ma_short > ma_mid) & (ma_mid > ma_long)

def composite_index_with_weights(prices, volume, weight_stock_info, weights=[0.4, 0.35, 0.25]):
    ma_short = calculate_ma(prices, 5)
    ma_mid = calculate_ma(prices, 20)
    ma_long = calculate_ma(prices, 60)
    
    three_line_bullish = is_bullish(ma_short, ma_mid, ma_long)

    base_line = weights[0]*ma_short + weights[1]*ma_mid + weights[2]*ma_long

    max_vol = volume.rolling(window=60).max()
    vol_factor = 1 + volume / (max_vol + 1e-9)

    weighted_sum = 0
    for stock_name, info in weight_stock_info.items():
        bullish_binary = info['bullish'].astype(int)
        weighted_sum += info['alpha'] * bullish_binary * (info['weighted_ma'] / info['price'])

    final_index = base_line * vol_factor * (1 + weighted_sum)

    return pd.DataFrame({
        'Price': prices,
        'MA_5': ma_short,
        'MA_20': ma_mid,
        'MA_60': ma_long,
        'Three_Line_Bullish': three_line_bullish,
        'Base_Line': base_line,
        'Vol_Factor': vol_factor,
        'Weighted_Stock_Sum': weighted_sum,
        'Final_Index': final_index
    })

# 建立模擬資料
dates = pd.date_range(start='2025-05-01', periods=100)
np.random.seed(0)

market_price = pd.Series(23000 + np.random.normal(0, 50, size=100).cumsum(), index=dates)
market_volume = pd.Series(np.random.randint(2000, 6000, size=100), index=dates)

stock1_price = pd.Series(1150 + np.random.normal(0, 5, size=100).cumsum(), index=dates)
stock1_ma_short = calculate_ma(stock1_price, 5)
stock1_ma_mid = calculate_ma(stock1_price, 20)
stock1_ma_long = calculate_ma(stock1_price, 60)
stock1_bullish = is_bullish(stock1_ma_short, stock1_ma_mid, stock1_ma_long)
stock1_weighted_ma = 0.4*stock1_ma_short + 0.35*stock1_ma_mid + 0.25*stock1_ma_long

stock2_price = pd.Series(900 + np.random.normal(0, 10, size=100).cumsum(), index=dates)
stock2_ma_short = calculate_ma(stock2_price, 5)
stock2_ma_mid = calculate_ma(stock2_price, 20)
stock2_ma_long = calculate_ma(stock2_price, 60)
stock2_bullish = is_bullish(stock2_ma_short, stock2_ma_mid, stock2_ma_long)
stock2_weighted_ma = 0.4*stock2_ma_short + 0.35*stock2_ma_mid + 0.25*stock2_ma_long

weight_stock_info = {
    'stock1': {'alpha':0.3, 'bullish':stock1_bullish, 'weighted_ma':stock1_weighted_ma, 'price':stock1_price},
    'stock2': {'alpha':0.2, 'bullish':stock2_bullish, 'weighted_ma':stock2_weighted_ma, 'price':stock2_price}
}

df = composite_index_with_weights(market_price, market_volume, weight_stock_info)

# 繪圖
plt.figure(figsize=(14,8))

# 股價和均線
plt.plot(df.index, df['Price'], label='大盤收盤價', color='black')
plt.plot(df.index, df['MA_5'], label='5日均線', linestyle='--')
plt.plot(df.index, df['MA_20'], label='20日均線', linestyle='--')
plt.plot(df.index, df['MA_60'], label='60日均線', linestyle='--')

# 多頭排列區間底色
bullish = df['Three_Line_Bullish']
plt.fill_between(df.index, df['Price'].min(), df['Price'].max(), where=bullish, color='lightgreen', alpha=0.3, label='三線多頭區間')

# 最終大盤線
plt.plot(df.index, df['Final_Index'], label='強化大盤線(含權值股、成交量)', color='red', linewidth=2)

plt.title('強化版大盤線與三線架構示範')
plt.xlabel('日期')
plt.ylabel('價格')
plt.legend()
plt.grid(True)
plt.show()
