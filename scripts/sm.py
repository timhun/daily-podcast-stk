#!/usr/bin/env python3
“””
策略大師 (Strategy Mastermind)
AI驅動的量化策略競技與最佳化引擎

Author: 幫幫忙 AI
Version: 1.0.0
“””

import pandas as pd
import numpy as np
import yfinance as yf
import talib
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from datetime import datetime, timedelta
import requests
import json
import logging
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings(‘ignore’)

# 配置日誌

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(**name**)

class TechnicalAnalysisStrategy:
“”“技術分析策略”””

```
def __init__(self, name="Technical Analysis"):
    self.name = name
    self.signals = {}
    
def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
    """計算技術指標"""
    df = data.copy()
    
    # 移動平均線
    df['SMA_20'] = talib.SMA(df['Close'], timeperiod=20)
    df['SMA_50'] = talib.SMA(df['Close'], timeperiod=50)
    df['EMA_12'] = talib.EMA(df['Close'], timeperiod=12)
    df['EMA_26'] = talib.EMA(df['Close'], timeperiod=26)
    
    # 動量指標
    df['RSI'] = talib.RSI(df['Close'], timeperiod=14)
    df['MACD'], df['MACD_signal'], df['MACD_hist'] = talib.MACD(
        df['Close'], fastperiod=12, slowperiod=26, signalperiod=9
    )
    df['Stoch_K'], df['Stoch_D'] = talib.STOCH(
        df['High'], df['Low'], df['Close']
    )
    
    # 波動率指標
    df['BB_upper'], df['BB_middle'], df['BB_lower'] = talib.BBANDS(
        df['Close'], timeperiod=20, nbdevup=2, nbdevdn=2
    )
    df['ATR'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)
    
    # 成交量指標
    df['OBV'] = talib.OBV(df['Close'], df['Volume'])
    df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
    
    return df

def generate_signals(self, data: pd.DataFrame) -> Dict:
    """生成交易信號"""
    df = self.calculate_indicators(data)
    latest = df.iloc[-1]
    
    signals = {
        'trend_signals': {},
        'momentum_signals': {},
        'volume_signals': {},
        'overall_score': 0
    }
    
    # 趨勢信號
    if latest['Close'] > latest['SMA_20'] > latest['SMA_50']:
        signals['trend_signals']['ma_trend'] = {'signal': 'BUY', 'strength': 0.8}
    elif latest['Close'] < latest['SMA_20'] < latest['SMA_50']:
        signals['trend_signals']['ma_trend'] = {'signal': 'SELL', 'strength': 0.8}
    else:
        signals['trend_signals']['ma_trend'] = {'signal': 'NEUTRAL', 'strength': 0.3}
    
    # 動量信號
    if latest['RSI'] < 30:
        signals['momentum_signals']['rsi'] = {'signal': 'BUY', 'strength': 0.7}
    elif latest['RSI'] > 70:
        signals['momentum_signals']['rsi'] = {'signal': 'SELL', 'strength': 0.7}
    else:
        signals['momentum_signals']['rsi'] = {'signal': 'NEUTRAL', 'strength': 0.2}
    
    if latest['MACD'] > latest['MACD_signal']:
        signals['momentum_signals']['macd'] = {'signal': 'BUY', 'strength': 0.6}
    else:
        signals['momentum_signals']['macd'] = {'signal': 'SELL', 'strength': 0.6}
    
    # 成交量確認
    volume_ratio = latest['Volume'] / latest['Volume_MA']
    if volume_ratio > 1.5:
        signals['volume_signals']['volume_confirm'] = {'signal': 'STRONG', 'strength': 0.5}
    elif volume_ratio > 1.2:
        signals['volume_signals']['volume_confirm'] = {'signal': 'MODERATE', 'strength': 0.3}
    else:
        signals['volume_signals']['volume_confirm'] = {'signal': 'WEAK', 'strength': 0.1}
    
    # 計算綜合評分
    signals['overall_score'] = self.calculate_overall_score(signals)
    
    return signals

def calculate_overall_score(self, signals: Dict) -> float:
    """計算綜合技術分析評分"""
    total_score = 0
    max_score = 0
    
    for category in ['trend_signals', 'momentum_signals', 'volume_signals']:
        for signal_name, signal_data in signals[category].items():
            strength = signal_data['strength']
            signal_type = signal_data['signal']
            
            if signal_type == 'BUY' or signal_type == 'STRONG':
                total_score += strength
            elif signal_type == 'SELL':
                total_score -= strength
            # NEUTRAL 和 WEAK 不加分也不減分
            
            max_score += strength
    
    # 正規化到 -1 到 1 之間
    if max_score > 0:
        return total_score / max_score
    return 0

def backtest(self, symbol: str, timeframe: str = '1d', period: str = '1y') -> Dict:
    """回測策略表現"""
    try:
        # 下載歷史數據
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=timeframe)
        
        if len(data) < 50:
            return {'error': 'Insufficient data for backtesting'}
        
        # 計算指標
        data_with_indicators = self.calculate_indicators(data)
        
        # 簡化回測邏輯
        returns = []
        positions = []
        
        for i in range(50, len(data_with_indicators)):
            current_data = data_with_indicators.iloc[:i+1]
            signals = self.generate_signals(current_data)
            score = signals['overall_score']
            
            # 根據評分決定倉位
            if score > 0.3:
                position = 1  # 做多
            elif score < -0.3:
                position = -1  # 做空
            else:
                position = 0  # 空倉
            
            positions.append(position)
            
            # 計算收益
            if i > 50:  # 需要前一期的倉位
                prev_position = positions[-2]
                price_return = (data.iloc[i]['Close'] / data.iloc[i-1]['Close'] - 1)
                strategy_return = prev_position * price_return
                returns.append(strategy_return)
        
        # 計算績效指標
        returns = np.array(returns)
        
        total_return = (1 + returns).prod() - 1
        volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        max_drawdown = self.calculate_max_drawdown(returns)
        win_rate = (returns > 0).mean()
        
        return {
            'strategy': self.name,
            'symbol': symbol,
            'total_return': total_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': len(returns)
        }
        
    except Exception as e:
        logger.error(f"技術分析策略回測失敗: {e}")
        return {'error': str(e)}

def calculate_max_drawdown(self, returns: np.array) -> float:
    """計算最大回撤"""
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative / running_max) - 1
    return drawdown.min()
```

class RandomForestStrategy:
“”“隨機森林機器學習策略”””

```
def __init__(self, name="Random Forest ML"):
    self.name = name
    self.model = RandomForestRegressor(n_estimators=100, random_state=42)
    self.scaler = StandardScaler()
    self.is_trained = False
    
def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
    """準備機器學習特徵"""
    df = data.copy()
    
    # 價格特徵
    df['returns'] = df['Close'].pct_change()
    df['returns_1d'] = df['returns'].shift(1)
    df['returns_3d'] = df['returns'].rolling(3).mean()
    df['returns_7d'] = df['returns'].rolling(7).mean()
    
    # 技術指標特徵
    df['rsi'] = talib.RSI(df['Close'])
    df['macd'], _, _ = talib.MACD(df['Close'])
    df['bb_position'] = (df['Close'] - talib.BBANDS(df['Close'])[2]) / (talib.BBANDS(df['Close'])[0] - talib.BBANDS(df['Close'])[2])
    
    # 成交量特徵
    df['volume_ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
    df['price_volume'] = df['Close'] * df['Volume']
    
    # 波動率特徵
    df['volatility'] = df['returns'].rolling(20).std()
    df['high_low_ratio'] = df['High'] / df['Low']
    
    # 趨勢特徵
    df['sma_20'] = talib.SMA(df['Close'], 20)
    df['sma_50'] = talib.SMA(df['Close'], 50)
    df['trend_strength'] = (df['Close'] - df['sma_50']) / df['sma_50']
    
    return df

def train(self, data: pd.DataFrame):
    """訓練機器學習模型"""
    df = self.prepare_features(data)
    
    # 準備特徵和目標變數
    feature_columns = [
        'returns_1d', 'returns_3d', 'returns_7d', 'rsi', 'macd',
        'bb_position', 'volume_ratio', 'volatility', 'high_low_ratio',
        'trend_strength'
    ]
    
    # 目標變數：未來5日收益率
    df['target'] = df['Close'].shift(-5) / df['Close'] - 1
    
    # 清理數據
    df = df.dropna()
    
    if len(df) < 100:
        raise ValueError("訓練數據不足")
    
    X = df[feature_columns].values
    y = df['target'].values
    
    # 標準化特徵
    X_scaled = self.scaler.fit_transform(X)
    
    # 訓練模型
    self.model.fit(X_scaled, y)
    self.is_trained = True
    
    logger.info(f"隨機森林模型訓練完成，樣本數: {len(X)}")

def predict(self, data: pd.DataFrame) -> float:
    """預測未來收益率"""
    if not self.is_trained:
        raise ValueError("模型尚未訓練")
    
    df = self.prepare_features(data)
    
    feature_columns = [
        'returns_1d', 'returns_3d', 'returns_7d', 'rsi', 'macd',
        'bb_position', 'volume_ratio', 'volatility', 'high_low_ratio',
        'trend_strength'
    ]
    
    # 取最新數據
    latest_features = df[feature_columns].iloc[-1:].values
    latest_features_scaled = self.scaler.transform(latest_features)
    
    prediction = self.model.predict(latest_features_scaled)[0]
    return prediction

def backtest(self, symbol: str, timeframe: str = '1d', period: str = '2y') -> Dict:
    """回測隨機森林策略"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=timeframe)
        
        if len(data) < 200:
            return {'error': 'Insufficient data for ML backtesting'}
        
        # 分割訓練和測試數據
        split_point = int(len(data) * 0.7)
        train_data = data.iloc[:split_point]
        test_data = data.iloc[split_point:]
        
        # 訓練模型
        self.train(train_data)
        
        # 測試預測
        returns = []
        predictions = []
        
        for i in range(50, len(test_data)-5):
            current_data = pd.concat([train_data, test_data.iloc[:i+1]])
            prediction = self.predict(current_data)
            predictions.append(prediction)
            
            # 根據預測決定倉位
            if prediction > 0.02:  # 預測收益 > 2%
                position = 1
            elif prediction < -0.02:  # 預測虧損 > 2%
                position = -1
            else:
                position = 0
            
            # 計算實際收益
            actual_return = (test_data.iloc[i+5]['Close'] / test_data.iloc[i]['Close'] - 1)
            strategy_return = position * actual_return
            returns.append(strategy_return)
        
        # 計算績效
        returns = np.array(returns)
        total_return = (1 + returns).prod() - 1
        volatility = returns.std() * np.sqrt(252/5)  # 5日調整
        sharpe_ratio = (returns.mean() * 252/5) / (returns.std() * np.sqrt(252/5)) if returns.std() > 0 else 0
        max_drawdown = self.calculate_max_drawdown(returns)
        win_rate = (returns > 0).mean()
        
        return {
            'strategy': self.name,
            'symbol': symbol,
            'total_return': total_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': len(returns),
            'avg_prediction': np.mean(predictions)
        }
        
    except Exception as e:
        logger.error(f"隨機森林策略回測失敗: {e}")
        return {'error': str(e)}

def calculate_max_drawdown(self, returns: np.array) -> float:
    """計算最大回撤"""
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative / running_max) - 1
    return drawdown.min()
```

class LSTMStrategy:
“”“LSTM深度學習策略”””

```
def __init__(self, name="LSTM Deep Learning", sequence_length=60):
    self.name = name
    self.sequence_length = sequence_length
    self.model = None
    self.scaler = StandardScaler()
    self.is_trained = False
    
def prepare_sequences(self, data: np.array) -> Tuple[np.array, np.array]:
    """準備LSTM序列數據"""
    X, y = [], []
    for i in range(self.sequence_length, len(data)):
        X.append(data[i-self.sequence_length:i])
        y.append(data[i])
    return np.array(X), np.array(y)

def build_model(self, input_shape: Tuple):
    """構建LSTM模型"""
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(50, return_sequences=True),
        Dropout(0.2),
        LSTM(50),
        Dropout(0.2),
        Dense(1)
    ])
    
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model

def train(self, data: pd.DataFrame):
    """訓練LSTM模型"""
    # 準備特徵數據
    features = data[['Close', 'Volume', 'High', 'Low']].values
    
    # 標準化
    features_scaled = self.scaler.fit_transform(features)
    
    # 準備序列
    X, y = self.prepare_sequences(features_scaled[:, 0])  # 使用收盤價作為目標
    
    if len(X) < 100:
        raise ValueError("LSTM訓練數據不足")
    
    # 構建模型
    self.model = self.build_model((X.shape[1], 1))
    
    # 重塑X的形狀
    X = X.reshape((X.shape[0], X.shape[1], 1))
    
    # 訓練模型
    self.model.fit(X, y, epochs=50, batch_size=32, verbose=0)
    self.is_trained = True
    
    logger.info(f"LSTM模型訓練完成，樣本數: {len(X)}")

def predict(self, data: pd.DataFrame) -> float:
    """LSTM預測"""
    if not self.is_trained:
        raise ValueError("LSTM模型尚未訓練")
    
    features = data[['Close', 'Volume', 'High', 'Low']].values
    features_scaled = self.scaler.transform(features)
    
    # 取最後sequence_length個數據點
    last_sequence = features_scaled[-self.sequence_length:, 0]
    last_sequence = last_sequence.reshape((1, self.sequence_length, 1))
    
    # 預測
    prediction_scaled = self.model.predict(last_sequence, verbose=0)[0, 0]
    
    # 反標準化（簡化處理）
    current_price = data['Close'].iloc[-1]
    predicted_price = current_price * (1 + prediction_scaled * 0.1)  # 假設10%的變動範圍
    
    return (predicted_price / current_price) - 1

def backtest(self, symbol: str, timeframe: str = '1d', period: str = '2y') -> Dict:
    """LSTM策略回測"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=timeframe)
        
        if len(data) < 300:
            return {'error': 'LSTM需要更多歷史數據'}
        
        # 分割數據
        split_point = int(len(data) * 0.8)
        train_data = data.iloc[:split_point]
        test_data = data.iloc[split_point:]
        
        # 訓練模型
        self.train(train_data)
        
        # 測試預測
        returns = []
        
        for i in range(self.sequence_length, len(test_data)-1):
            current_data = pd.concat([train_data, test_data.iloc[:i+1]])
            prediction = self.predict(current_data)
            
            # 根據預測決定倉位
            if prediction > 0.01:
                position = 1
            elif prediction < -0.01:
                position = -1
            else:
                position = 0
            
            # 計算收益
            actual_return = (test_data.iloc[i+1]['Close'] / test_data.iloc[i]['Close'] - 1)
            strategy_return = position * actual_return
            returns.append(strategy_return)
        
        # 計算績效
        returns = np.array(returns)
        total_return = (1 + returns).prod() - 1
        volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        max_drawdown = self.calculate_max_drawdown(returns)
        win_rate = (returns > 0).mean()
        
        return {
            'strategy': self.name,
            'symbol': symbol,
            'total_return': total_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': len(returns)
        }
        
    except Exception as e:
        logger.error(f"LSTM策略回測失敗: {e}")
        return {'error': str(e)}

def calculate_max_drawdown(self, returns: np.array) -> float:
    """計算最大回撤"""
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative / running_max) - 1
    return drawdown.min()
```

class SentimentStrategy:
“”“市場情緒策略”””

```
def __init__(self, name="Market Sentiment"):
    self.name = name
    
def get_fear_greed_index(self) -> float:
    """獲取恐懼貪婪指數（模擬）"""
    # 這裡應該調用真實的API，現在返回隨機值作為示例
    import random
    return random.uniform(0, 100)

def analyze_sentiment(self, symbol: str) -> Dict:
    """分析市場情緒"""
    try:
        # 獲取VIX數據
        vix = yf.Ticker("^VIX")
        vix_data = vix.history(period="30d")
        current_vix = vix_data['Close'].iloc[-1]
        vix_avg = vix_data['Close'].mean()
        
        # 獲取恐懼貪婪指數
        fear_greed = self.get_fear_greed_index()
        
        # 情緒評分
        sentiment_score = 0
        
        # VIX分析
        if current_vix < 20:
            sentiment_score += 0.3  # 低恐慌，偏樂觀
        elif current_vix > 30:
            sentiment_score -= 0.3  # 高恐慌，偏悲觀
        
        # VIX趨勢
        if current_vix < vix_avg:
            sentiment_score += 0.2  # VIX下降，情緒改善
        else:
            sentiment_score -= 0.2  # VIX上升，情緒惡化
        
        # 恐懼貪婪指數
        if fear_greed > 70:
            sentiment_score -= 0.2  # 極度貪婪，可能回調
        elif fear_greed < 30:
            sentiment_score += 0.2  # 極度恐懼，可能反彈
        
        return {
            'sentiment_score': sentiment_score,
            'vix_current': current_vix,
            'vix_average': vix_avg,
            'fear_greed_index': fear_greed
        }
        
    except Exception as e:
        logger.error(f"情緒分析失敗: {e}")
        return {'sentiment_score': 0, 'error': str(e)}

def backtest(self, symbol: str, timeframe: str = '1d', period: str = '1y') -> Dict:
    """情緒策略回測"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=timeframe)
        
        # 獲取VIX數據
        vix = yf.Ticker("^VIX")
        vix_data = vix.history(period=period, interval=timeframe)
        
        # 對齊日期
        common_dates = data.index.intersection(vix_data.index)
        data = data.loc[common_dates]
        vix_data = vix_data.loc[common_dates]
        
        if len(data) < 50:
            return {'error': 'Insufficient data for sentiment backtesting'}
        
        returns = []
        
        for i in range(20, len(data)-1):
            # 計算VIX指標
            current_vix = vix_data['Close'].iloc[i]
            vix_avg = vix_data['Close'].iloc[i-20:i].mean()
            
            # 情緒評分
            sentiment_score = 0
            if current_vix < 20:
                sentiment_score += 0.5
            elif current_vix > 30:
                sentiment_score -= 0.5
            
            if current_vix < vix_avg:
                sentiment_score += 0.3
            else:
                sentiment_score -= 0.3
            
            # 交易信號
            if sentiment_score > 0.3:
                position = 1  # 樂觀做多
            elif sentiment_score < -0.3:
                position = -1  # 悲觀做空
            else:
                position = 0
            
            # 計算收益
            actual_return = (data['Close'].iloc[i+1] / data['Close'].iloc[i] - 1)
            strategy_return = position * actual_return
            returns.append(strategy_return)
        
        # 計算績效
        returns = np.array(returns)
        total_return = (1 + returns).prod() - 1
        volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        max_drawdown = self.calculate_max_drawdown(returns)
        win_rate = (returns > 0).mean()
        
        return {
            'strategy': self.name,
            'symbol': symbol,
            'total_return': total_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': len(returns)
        }
        
    except Exception as e:
        logger.error(f"情緒策略回測失敗: {e}")
        return {'error': str(e)}

def calculate_max_drawdown(self, returns: np.array) -> float:
    """計算最大回撤"""
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative / running_max) - 1
    return drawdown.min()
```

class MacroEconomicStrategy:
“”“宏觀經濟策略”””

```
def __init__(self, name="Macro Economic"):
    self.name = name
    
def get_economic_indicators(self) -> Dict:
    """獲取經濟指標"""
    try:
        # 獲取美債殖利率
        ust_10y = yf.Ticker("^TNX")
        ust_data = ust_10y.history(period="30d")
        current_yield = ust_data['Close'].iloc[-1]
        
        # 獲取美元指數
        dxy = yf.Ticker("DX-Y.NYB")
        dxy_data = dxy.history(period="30d")
        current_dxy = dxy_data['Close'].iloc[-1] if not dxy_data.empty else 100
        
        # 獲取黃金價格
        gold = yf.Ticker("GC=F")
        gold_data = gold.history(period="30d")
        current_gold = gold_data['Close'].iloc[-1] if not gold_data.empty else 2000
        
        return {
            'ust_10y_yield': current_yield,
            'dxy_index': current_dxy,
            'gold_price': current_gold
        }
        
    except Exception as e:
        logger.error(f"經濟指標獲取失敗: {e}")
        return {}

def analyze_macro_environment(self) -> Dict:
    """分析宏觀環境"""
    indicators = self.get_economic_indicators()
    
    if not indicators:
        return {'macro_score': 0, 'error': 'Failed to get indicators'}
    
    macro_score = 0
    
    # 利率分析
    if 'ust_10y_yield' in indicators:
        yield_10y = indicators['ust_10y_yield']
        if yield_10y < 3:
            macro_score += 0.2  # 低利率利多股市
        elif yield_10y > 5:
            macro_score -= 0.2  # 高利率利空股市
    
    # 美元指數分析
    if 'dxy_index' in indicators:
        dxy = indicators['dxy_index']
        if dxy < 95:
            macro_score += 0.2  # 美元走弱利多股市
        elif dxy > 105:
            macro_score -= 0.2  # 美元走強利空股市
    
    # 黃金價格分析
    if 'gold_price' in indicators:
        gold = indicators['gold_price']
        if gold > 2100:
            macro_score -= 0.1  # 金價高企，避險情緒濃厚
        elif gold < 1800:
            macro_score += 0.1  # 金價低迷，風險偏好回升
    
    return {
        'macro_score': macro_score,
        'indicators': indicators,
        'analysis': self.generate_macro_analysis(indicators, macro_score)
    }

def generate_macro_analysis(self, indicators: Dict, score: float) -> str:
    """生成宏觀分析報告"""
    analysis = []
    
    if score > 0.2:
        analysis.append("宏觀環境整體偏多，利於風險資產")
    elif score < -0.2:
        analysis.append("宏觀環境整體偏空，建議謹慎操作")
    else:
        analysis.append("宏觀環境中性，需關注其他因素")
    
    if 'ust_10y_yield' in indicators:
        yield_val = indicators['ust_10y_yield']
        analysis.append(f"美債10年期殖利率: {yield_val:.2f}%")
    
    if 'dxy_index' in indicators:
        dxy_val = indicators['dxy_index']
        analysis.append(f"美元指數: {dxy_val:.2f}")
    
    return " | ".join(analysis)

def backtest(self, symbol: str, timeframe: str = '1d', period: str = '1y') -> Dict:
    """宏觀策略回測"""
    try:
        # 獲取標的數據
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=timeframe)
        
        # 獲取宏觀指標數據
        ust_10y = yf.Ticker("^TNX")
        ust_data = ust_10y.history(period=period, interval=timeframe)
        
        # 對齊日期
        common_dates = data.index.intersection(ust_data.index)
        data = data.loc[common_dates]
        ust_data = ust_data.loc[common_dates]
        
        if len(data) < 50:
            return {'error': 'Insufficient data for macro backtesting'}
        
        returns = []
        
        for i in range(20, len(data)-1):
            # 分析宏觀環境
            current_yield = ust_data['Close'].iloc[i]
            yield_trend = ust_data['Close'].iloc[i-5:i].mean() - ust_data['Close'].iloc[i-20:i-5].mean()
            
            # 宏觀評分
            macro_score = 0
            
            # 利率水平
            if current_yield < 3:
                macro_score += 0.3
            elif current_yield > 5:
                macro_score -= 0.3
            
            # 利率趨勢
            if yield_trend < -0.1:  # 利率下降
                macro_score += 0.2
            elif yield_trend > 0.1:  # 利率上升
                macro_score -= 0.2
            
            # 交易信號
            if macro_score > 0.2:
                position = 1
            elif macro_score < -0.2:
                position = -1
            else:
                position = 0
            
            # 計算收益
            actual_return = (data['Close'].iloc[i+1] / data['Close'].iloc[i] - 1)
            strategy_return = position * actual_return
            returns.append(strategy_return)
        
        # 計算績效
        returns = np.array(returns)
        total_return = (1 + returns).prod() - 1
        volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        max_drawdown = self.calculate_max_drawdown(returns)
        win_rate = (returns > 0).mean()
        
        return {
            'strategy': self.name,
            'symbol': symbol,
            'total_return': total_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': len(returns)
        }
        
    except Exception as e:
        logger.error(f"宏觀策略回測失敗: {e}")
        return {'error': str(e)}

def calculate_max_drawdown(self, returns: np.array) -> float:
    """計算最大回撤"""
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative / running_max) - 1
    return drawdown.min()
```

class GrokAPIOptimizer:
“”“Grok API優化器”””

```
def __init__(self, api_key: str = None):
    self.api_key = api_key or "your-grok-api-key"
    self.base_url = "https://api.x.ai/v1"
    
def optimize_portfolio(self, strategy_results: Dict) -> Dict:
    """使用Grok AI優化投資組合配置"""
    try:
        # 準備提示詞
        prompt = self.prepare_optimization_prompt(strategy_results)
        
        # 調用Grok API（這裡是模擬實現）
        optimization_result = self.call_grok_api(prompt)
        
        # 解析AI建議
        optimized_weights = self.parse_optimization_result(optimization_result)
        
        # 計算最終策略
        final_strategy = self.calculate_weighted_strategy(strategy_results, optimized_weights)
        
        return final_strategy
        
    except Exception as e:
        logger.error(f"Grok API優化失敗: {e}")
        # 返回等權重組合作為備案
        return self.equal_weight_fallback(strategy_results)

def prepare_optimization_prompt(self, results: Dict) -> str:
    """準備優化提示詞"""
    prompt = """
```

作為量化投資專家，請分析以下策略表現並給出最佳權重配置建議：

策略表現數據：
“””

```
    for strategy_name, result in results.items():
        if 'error' not in result:
            prompt += f"""
```

{strategy_name}:

- 總收益率: {result.get(‘total_return’, 0):.2%}
- 夏普比率: {result.get(‘sharpe_ratio’, 0):.2f}
- 最大回撤: {result.get(‘max_drawdown’, 0):.2%}
- 勝率: {result.get(‘win_rate’, 0):.2%}
  “””
  
  ```
    prompt += """
  ```

請基於以下原則給出權重建議：

1. 夏普比率高的策略權重較大
1. 最大回撤小的策略優先
1. 總體組合風險控制在15%以內
1. 至少包含3個不同類型的策略

請以JSON格式返回權重分配，總和為1.0
“””

```
    return prompt

def call_grok_api(self, prompt: str) -> str:
    """調用Grok API（模擬實現）"""
    # 這裡應該實際調用Grok API
    # 現在返回模擬結果
    mock_response = """
    {
        "weights": {
            "Technical Analysis": 0.35,
            "Random Forest ML": 0.25,
            "LSTM Deep Learning": 0.20,
            "Market Sentiment": 0.15,
            "Macro Economic": 0.05
        },
        "reasoning": "技術分析策略表現穩定，給予較高權重；機器學習策略具有適應性；情緒策略提供互補信號。"
    }
    """
    return mock_response

def parse_optimization_result(self, result: str) -> Dict:
    """解析AI優化結果"""
    try:
        import json
        data = json.loads(result)
        return data.get('weights', {})
    except:
        # 解析失敗時返回等權重
        return {
            "Technical Analysis": 0.3,
            "Random Forest ML": 0.25,
            "LSTM Deep Learning": 0.2,
            "Market Sentiment": 0.15,
            "Macro Economic": 0.1
        }

def calculate_weighted_strategy(self, results: Dict, weights: Dict) -> Dict:
    """計算加權策略組合"""
    weighted_metrics = {
        'total_return': 0,
        'sharpe_ratio': 0,
        'max_drawdown': 0,
        'win_rate': 0,
        'volatility': 0
    }
    
    valid_strategies = []
    total_weight = 0
    
    for strategy_name, weight in weights.items():
        if strategy_name in results and 'error' not in results[strategy_name]:
            valid_strategies.append(strategy_name)
            result = results[strategy_name]
            
            weighted_metrics['total_return'] += result.get('total_return', 0) * weight
            weighted_metrics['sharpe_ratio'] += result.get('sharpe_ratio', 0) * weight
            weighted_metrics['max_drawdown'] += result.get('max_drawdown', 0) * weight
            weighted_metrics['win_rate'] += result.get('win_rate', 0) * weight
            weighted_metrics['volatility'] += result.get('volatility', 0) * weight
            
            total_weight += weight
    
    # 正規化權重
    if total_weight > 0:
        for metric in weighted_metrics:
            weighted_metrics[metric] /= total_weight
    
    return {
        'strategy': 'AI Optimized Portfolio',
        'valid_strategies': valid_strategies,
        'weights': weights,
        **weighted_metrics,
        'confidence': min(len(valid_strategies) / 5.0, 1.0)
    }

def equal_weight_fallback(self, results: Dict) -> Dict:
    """等權重備案組合"""
    valid_results = {k: v for k, v in results.items() if 'error' not in v}
    
    if not valid_results:
        return {'error': 'No valid strategies available'}
    
    weight = 1.0 / len(valid_results)
    weights = {strategy: weight for strategy in valid_results.keys()}
    
    return self.calculate_weighted_strategy(results, weights)
```

class StrategyEngine:
“”“策略引擎主類”””

```
def __init__(self, grok_api_key: str = None):
    self.models = {
        'technical': TechnicalAnalysisStrategy(),
        'ml_forest': RandomForestStrategy(),
        'dl_lstm': LSTMStrategy(),
        'sentiment': SentimentStrategy(),
        'macro': MacroEconomicStrategy()
    }
    self.grok_optimizer = GrokAPIOptimizer(grok_api_key)
    self.benchmark_symbols = {
        'us': '^GSPC',  # S&P 500
        'tw': '^TWII'   # 台股加權指數
    }

def run_strategy_tournament(self, symbol: str, timeframe: str = '1d', period: str = '1y') -> Dict:
    """執行策略競技"""
    logger.info(f"開始策略競技: {symbol}")
    
    results = {}
    
    # 並行執行所有策略回測
    for name, strategy in self.models.items():
        logger.info(f"執行策略: {name}")
        result = strategy.backtest(symbol, timeframe, period)
        results[name] = result
        
        if 'error' in result:
            logger.warning(f"策略 {name} 執行失敗: {result['error']}")
        else:
            logger.info(f"策略 {name} 完成 - 收益: {result['total_return']:.2%}, 夏普: {result['sharpe_ratio']:.2f}")
    
    # 獲取基準表現
    market = 'us' if any(x in symbol.upper() for x in ['SPY', 'QQQ', 'NVDA', 'AAPL']) else 'tw'
    benchmark = self.get_benchmark_performance(market, timeframe, period)
    
    # Grok AI 優化組合
    logger.info("執行AI優化...")
    optimized = self.grok_optimizer.optimize_portfolio(results)
    
    # 生成最終信號
    final_signals = self.generate_final_signals(symbol, optimized, benchmark)
    
    return {
        'symbol': symbol,
        'analysis_date': datetime.now().strftime('%Y-%m-%d'),
        'individual_strategies': results,
        'benchmark': benchmark,
        'optimized_portfolio': optimized,
        'final_recommendation': final_signals
    }

def get_benchmark_performance(self, market: str, timeframe: str, period: str) -> Dict:
    """獲取基準表現"""
    try:
        benchmark_symbol = self.benchmark_symbols[market]
        ticker = yf.Ticker(benchmark_symbol)
        data = ticker.history(period=period, interval=timeframe)
        
        returns = data['Close'].pct_change().dropna()
        total_return = (data['Close'].iloc[-1] / data['Close'].iloc[0]) - 1
        volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = (returns.mean() * 252) / volatility if volatility > 0 else 0
        
        return {
            'symbol': benchmark_symbol,
            'total_return': total_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio
        }
        
    except Exception as e:
        logger.error(f"基準指標獲取失敗: {e}")
        return {'error': str(e)}

def generate_final_signals(self, symbol: str, optimized: Dict, benchmark: Dict) -> Dict:
    """生成最終交易信號"""
    if 'error' in optimized:
        return {'error': 'Unable to generate signals due to optimization failure'}
    
    # 獲取當前價格
    try:
        ticker = yf.Ticker(symbol)
        current_data = ticker.history(period='5d')
        current_price = current_data['Close'].iloc[-1]
        
        # 基於優化後的組合表現決定信號
        expected_return = optimized.get('total_return', 0)
        confidence = optimized.get('confidence', 0)
        sharpe_ratio = optimized.get('sharpe_ratio', 0)
        max_drawdown = abs(optimized.get('max_drawdown', 0))
        
        # 信號強度計算
        signal_strength = 0
        
        # 收益率影響
        if expected_return > 0.1:  # 預期收益 > 10%
            signal_strength += 0.4
        elif expected_return > 0.05:  # 預期收益 > 5%
            signal_strength += 0.2
        elif expected_return < -0.05:  # 預期虧損 > 5%
            signal_strength -= 0.3
        
        # 夏普比率影響
        if sharpe_ratio > 1.0:
            signal_strength += 0.3
        elif sharpe_ratio < 0.5:
            signal_strength -= 0.2
        
        # 最大回撤影響
        if max_drawdown > 0.15:  # 回撤超過15%
            signal_strength -= 0.2
        
        # 信心度影響
        signal_strength *= confidence
        
        # 生成具體建議
        if signal_strength > 0.5:
            position = 'LONG'
            position_size = min(0.8, signal_strength)
        elif signal_strength < -0.3:
            position = 'SHORT'
            position_size = min(0.6, abs(signal_strength))
        else:
            position = 'NEUTRAL'
            position_size = 0
        
        # 計算目標價位和停損點
        if position == 'LONG':
            target_price = current_price * (1 + expected_return * 0.8)
            stop_loss = current_price * (1 - max_drawdown * 0.5)
        elif position == 'SHORT':
            target_price = current_price * (1 + expected_return * 0.8)  # 做空時收益為負
            stop_loss = current_price * (1 + max_drawdown * 0.5)
        else:
            target_price = current_price
            stop_loss = current_price
        
        return {
            'position': position,
            'entry_price': current_price,
            'target_price': target_price,
            'stop_loss': stop_loss,
            'position_size': position_size,
            'expected_return': expected_return,
            'confidence': confidence,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'signal_strength': signal_strength,
            'risk_level': self.calculate_risk_level(max_drawdown, volatility=optimized.get('volatility', 0))
        }
        
    except Exception as e:
        logger.error(f"信號生成失敗: {e}")
        return {'error': str(e)}

def calculate_risk_level(self, max_drawdown: float, volatility: float) -> str:
    """計算風險等級"""
    risk_score = abs(max_drawdown) * 0.6 + volatility * 0.4
    
    if risk_score < 0.1:
        return "低風險 🟢"
    elif risk_score < 0.2:
        return "中低風險 🟡"
    elif risk_score < 0.3:
        return "中風險 🟠"
    else:
        return "高風險 🔴"

def save_analysis_result(self, result: Dict, output_path: str = None):
    """保存分析結果"""
    if not output_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"data/analysis/strategy_analysis_{result['symbol']}_{timestamp}.json"
    
    try:
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"分析結果已保存: {output_path}")
        
    except Exception as e:
        logger.error(f"結果保存失敗: {e}")
```

def main():
“”“主程序示例”””
import argparse

```
parser = argparse.ArgumentParser(description='策略大師 - 量化分析引擎')
parser.add_argument('--symbols', type=str, default='QQQ,0050.TW', 
                   help='分析標的，多個用逗號分隔')
parser.add_argument('--mode', type=str, choices=['us', 'tw'], default='us',
                   help='市場模式')
parser.add_argument('--period', type=str, default='1y',
                   help='分析時間範圍')
parser.add_argument('--grok-api-key', type=str, 
                   help='Grok API密鑰')

args = parser.parse_args()

# 初始化引擎
engine = StrategyEngine(grok_api_key=args.grok_api_key)

# 分析每個標的
symbols = args.symbols.split(',')

for symbol in symbols:
    symbol = symbol.strip()
    logger.info(f"開始分析: {symbol}")
    
    # 執行策略競技
    result = engine.run_strategy_tournament(
        symbol=symbol,
        period=args.period
    )
    
    # 保存結果
    engine.save_analysis_result(result)
    
    # 輸出摘要
    if 'final_recommendation' in result and 'error' not in result['final_recommendation']:
        rec = result['final_recommendation']
        print(f"\n=== {symbol} 分析結果 ===")
        print(f"建議部位: {rec['position']}")
        print(f"當前價格: {rec['entry_price']:.2f}")
        print(f"目標價格: {rec['target_price']:.2f}")
        print(f"停損價格: {rec['stop_loss']:.2f}")
        print(f"建議倉位: {rec['position_size']:.1%}")
        print(f"預期收益: {rec['expected_return']:.2%}")
        print(f"信心指數: {rec['confidence']:.2%}")
        print(f"風險等級: {rec['risk_level']}")
        print(f"夏普比率: {rec['sharpe_ratio']:.2f}")
    else:
        print(f"\n{symbol} 分析失敗或無有效建議")
```

if **name** == “**main**”:
main()