#!/usr/bin/env python3

import pandas as pd
import numpy as np
import yfinance as yf
import talib
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Tuple, Optional
import warnings

warnings.filterwarnings('ignore')

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketIntelligenceAnalyst:
    """市場解析師主類"""

    def __init__(self):
        self.indicators = {
            'trend': ['SMA_20', 'SMA_50', 'EMA_12', 'EMA_26', 'ADX'],
            'momentum': ['RSI_14', 'MACD', 'Stochastic', 'CCI', 'Williams_R'],
            'volume': ['OBV', 'Volume_MA', 'VWAP', 'A/D_Line'],
            'volatility': ['Bollinger_Bands', 'ATR', 'Keltner_Channel']
        }
        self.analysis_weights = {
            'trend': 0.35,
            'momentum': 0.25,
            'volume': 0.20,
            'volatility': 0.20
        }

    def comprehensive_analysis(self, symbol: str, strategy_result: Dict, period: str = '6mo') -> Dict:
        """執行全面市場分析"""
        logger.info(f"開始市場解析: {symbol}")
        
        try:
            # 獲取市場數據
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if len(data) < 50:
                return {'error': 'Insufficient market data'}
            
            # 各維度分析
            trend_analysis = self.analyze_trend(data)
            momentum_analysis = self.analyze_momentum(data)
            volume_analysis = self.analyze_volume(data)
            volatility_analysis = self.analyze_volatility(data)
            
            # 技術面綜合評分
            technical_score = self.calculate_technical_score({
                'trend': trend_analysis,
                'momentum': momentum_analysis,
                'volume': volume_analysis,
                'volatility': volatility_analysis
            })
            
            # 整合策略結果
            integrated_analysis = self.integrate_with_strategy(
                technical_score, strategy_result
            )
            
            # 風險評估
            risk_assessment = self.assess_risk_level(data, volatility_analysis)
            
            # 生成投資建議
            investment_advice = self.generate_investment_advice(
                integrated_analysis, risk_assessment
            )
            
            return {
                'symbol': symbol,
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'trend_analysis': trend_analysis,
                'momentum_analysis': momentum_analysis,
                'volume_analysis': volume_analysis,
                'volatility_analysis': volatility_analysis,
                'technical_score': technical_score,
                'integrated_analysis': integrated_analysis,
                'risk_assessment': risk_assessment,
                'investment_advice': investment_advice,
                'market_regime': self.identify_market_regime(data),
                'key_levels': self.calculate_key_levels(data)
            }
            
        except Exception as e:
            logger.error(f"市場分析失敗: {e}")
            return {'error': str(e)}

    def analyze_trend(self, data: pd.DataFrame) -> Dict:
        """趨勢分析"""
        df = data.copy()
        
        # 計算移動平均線
        df['SMA_20'] = talib.SMA(df['Close'], timeperiod=20)
        df['SMA_50'] = talib.SMA(df['Close'], timeperiod=50)
        df['SMA_200'] = talib.SMA(df['Close'], timeperiod=200)
        df['EMA_12'] = talib.EMA(df['Close'], timeperiod=12)
        df['EMA_26'] = talib.EMA(df['Close'], timeperiod=26)
        
        # ADX 趨勢強度
        df['ADX'] = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=14)
        
        latest = df.iloc[-1]
        latest_5 = df.iloc[-5:]
        
        analysis = {
            'ma_alignment': self.check_ma_alignment(latest),
            'trend_strength': self.calculate_trend_strength(latest, latest_5),
            'adx_reading': float(latest['ADX']) if not pd.isna(latest['ADX']) else 0,
            'price_ma_relationship': self.analyze_price_ma_relationship(latest),
            'trend_direction': self.determine_trend_direction(latest),
            'trend_score': 0
        }
        
        # 計算趨勢評分
        analysis['trend_score'] = self.calculate_trend_score(analysis)
        
        return analysis

    def check_ma_alignment(self, latest: pd.Series) -> Dict:
        """檢查移動平均線排列"""
        price = latest['Close']
        sma_20 = latest['SMA_20']
        sma_50 = latest['SMA_50']
        sma_200 = latest['SMA_200']
        
        if pd.isna(sma_200):
            return {'status': 'insufficient_data', 'score': 0}
        
        # 多頭排列：價格 > SMA20 > SMA50 > SMA200
        if price > sma_20 > sma_50 > sma_200:
            return {'status': 'bullish_alignment', 'score': 1.0}
        # 空頭排列：價格 < SMA20 < SMA50 < SMA200
        elif price < sma_20 < sma_50 < sma_200:
            return {'status': 'bearish_alignment', 'score': -1.0}
        # 部分多頭
        elif price > sma_20 and sma_20 > sma_50:
            return {'status': 'partial_bullish', 'score': 0.5}
        # 部分空頭
        elif price < sma_20 and sma_20 < sma_50:
            return {'status': 'partial_bearish', 'score': -0.5}
        else:
            return {'status': 'mixed', 'score': 0}

    def calculate_trend_strength(self, latest: pd.Series, recent: pd.DataFrame) -> Dict:
        """計算趨勢強度"""
        adx = latest['ADX']
        
        if pd.isna(adx):
            return {'strength': 'unknown', 'score': 0}
        
        # ADX 趨勢強度判斷
        if adx > 40:
            strength = 'very_strong'
            score = 1.0
        elif adx > 30:
            strength = 'strong'
            score = 0.8
        elif adx > 20:
            strength = 'moderate'
            score = 0.6
        else:
            strength = 'weak'
            score = 0.3
        
        # 趨勢持續性檢查
        adx_trend = 'rising' if recent['ADX'].iloc[-1] > recent['ADX'].iloc[-3] else 'falling'
        
        return {
            'adx_value': float(adx),
            'strength': strength,
            'trend': adx_trend,
            'score': score
        }

    def analyze_price_ma_relationship(self, latest: pd.Series) -> Dict:
        """分析價格與移動平均線關係"""
        price = latest['Close']
        sma_20 = latest['SMA_20']
        sma_50 = latest['SMA_50']
        
        if pd.isna(sma_50):
            return {'relationship': 'insufficient_data', 'score': 0}
        
        # 計算價格相對位置
        price_vs_sma20 = (price / sma_20 - 1) * 100 if not pd.isna(sma_20) else 0
        price_vs_sma50 = (price / sma_50 - 1) * 100
        
        if price_vs_sma20 > 5 and price_vs_sma50 > 5:
            relationship = 'strong_above'
            score = 0.8
        elif price_vs_sma20 > 0 and price_vs_sma50 > 0:
            relationship = 'above'
            score = 0.4
        elif price_vs_sma20 < -5 and price_vs_sma50 < -5:
            relationship = 'strong_below'
            score = -0.8
        elif price_vs_sma20 < 0 and price_vs_sma50 < 0:
            relationship = 'below'
            score = -0.4
        else:
            relationship = 'mixed'
            score = 0
        
        return {
            'relationship': relationship,
            'price_vs_sma20_pct': round(price_vs_sma20, 2),
            'price_vs_sma50_pct': round(price_vs_sma50, 2),
            'score': score
        }

    def determine_trend_direction(self, latest: pd.Series) -> Dict:
        """判斷趨勢方向"""
        sma_20 = latest['SMA_20']
        sma_50 = latest['SMA_50']
        ema_12 = latest['EMA_12']
        ema_26 = latest['EMA_26']
        
        directions = []
        
        # EMA方向
        if not pd.isna(ema_12) and not pd.isna(ema_26):
            if ema_12 > ema_26:
                directions.append('up')
            else:
                directions.append('down')
        
        # SMA方向
        if not pd.isna(sma_20) and not pd.isna(sma_50):
            if sma_20 > sma_50:
                directions.append('up')
            else:
                directions.append('down')
        
        # 統計方向
        up_count = directions.count('up')
        down_count = directions.count('down')
        
        if up_count > down_count:
            direction = 'uptrend'
            score = 0.6
        elif down_count > up_count:
            direction = 'downtrend'
            score = -0.6
        else:
            direction = 'sideways'
            score = 0
        
        return {
            'direction': direction,
            'confidence': abs(up_count - down_count) / len(directions) if directions else 0,
            'score': score
        }

    def calculate_trend_score(self, analysis: Dict) -> float:
        """計算趨勢綜合評分"""
        scores = [
            analysis['ma_alignment']['score'] * 0.4,
            analysis['trend_strength']['score'] * 0.3,
            analysis['price_ma_relationship']['score'] * 0.2,
            analysis['trend_direction']['score'] * 0.1
        ]
        
        return sum(scores)

    def analyze_momentum(self, data: pd.DataFrame) -> Dict:
        """動量分析"""
        df = data.copy()
        
        # 計算動量指標
        df['RSI'] = talib.RSI(df['Close'], timeperiod=14)
        df['MACD'], df['MACD_signal'], df['MACD_hist'] = talib.MACD(
            df['Close'], fastperiod=12, slowperiod=26, signalperiod=9
        )
        df['Stoch_K'], df['Stoch_D'] = talib.STOCH(
            df['High'], df['Low'], df['Close']
        )
        df['CCI'] = talib.CCI(df['High'], df['Low'], df['Close'], timeperiod=14)
        df['Williams_R'] = talib.WILLR(df['High'], df['Low'], df['Close'], timeperiod=14)
        
        latest = df.iloc[-1]
        recent = df.iloc[-5:]
        
        analysis = {
            'rsi_analysis': self.analyze_rsi(latest, recent),
            'macd_analysis': self.analyze_macd(latest, recent),
            'stochastic_analysis': self.analyze_stochastic(latest, recent),
            'momentum_divergence': self.check_momentum_divergence(df),
            'momentum_score': 0
        }
        
        # 計算動量評分
        analysis['momentum_score'] = self.calculate_momentum_score(analysis)
        
        return analysis

    def analyze_rsi(self, latest: pd.Series, recent: pd.DataFrame) -> Dict:
        """RSI分析"""
        rsi = latest['RSI']
        
        if pd.isna(rsi):
            return {'status': 'insufficient_data', 'score': 0}
        
        # RSI超買超賣判斷
        if rsi > 80:
            status = 'extremely_overbought'
            score = -0.8
        elif rsi > 70:
            status = 'overbought'
            score = -0.6
        elif rsi < 20:
            status = 'extremely_oversold'
            score = 0.8
        elif rsi < 30:
            status = 'oversold'
            score = 0.6
        elif rsi > 60:
            status = 'bullish'
            score = 0.4
        elif rsi < 40:
            status = 'bearish'
            score = -0.4
        else:
            status = 'neutral'
            score = 0
        
        # RSI趨勢
        rsi_trend = 'rising' if recent['RSI'].iloc[-1] > recent['RSI'].iloc[-3] else 'falling'
        
        return {
            'rsi_value': float(rsi),
            'status': status,
            'trend': rsi_trend,
            'score': score
        }

    def analyze_macd(self, latest: pd.Series, recent: pd.DataFrame) -> Dict:
        """MACD分析"""
        macd = latest['MACD']
        macd_signal = latest['MACD_signal']
        macd_hist = latest['MACD_hist']
        
        if pd.isna(macd) or pd.isna(macd_signal):
            return {'status': 'insufficient_data', 'score': 0}
        
        # MACD信號判斷
        if macd > macd_signal and macd_hist > 0:
            if recent['MACD_hist'].iloc[-2] <= 0:  # 金叉
                status = 'golden_cross'
                score = 0.8
            else:
                status = 'bullish'
                score = 0.4
        elif macd < macd_signal and macd_hist < 0:
            if recent['MACD_hist'].iloc[-2] >= 0:  # 死叉
                status = 'death_cross'
                score = -0.8
            else:
                status = 'bearish'
                score = -0.4
        else:
            status = 'neutral'
            score = 0
        
        # MACD柱狀圖趨勢
        hist_trend = 'strengthening' if macd_hist > recent['MACD_hist'].iloc[-2] else 'weakening'
        
        return {
            'macd_value': float(macd),
            'signal_value': float(macd_signal),
            'histogram': float(macd_hist),
            'status': status,
            'histogram_trend': hist_trend,
            'score': score
        }

    def analyze_stochastic(self, latest: pd.Series, recent: pd.DataFrame) -> Dict:
        """隨機指標分析"""
        stoch_k = latest['Stoch_K']
        stoch_d = latest['Stoch_D']
        
        if pd.isna(stoch_k) or pd.isna(stoch_d):
            return {'status': 'insufficient_data', 'score': 0}
        
        # 隨機指標判斷
        if stoch_k > 80 and stoch_d > 80:
            status = 'overbought'
            score = -0.6
        elif stoch_k < 20 and stoch_d < 20:
            status = 'oversold'
            score = 0.6
        elif stoch_k > stoch_d and stoch_k > 50:
            status = 'bullish'
            score = 0.4
        elif stoch_k < stoch_d and stoch_k < 50:
            status = 'bearish'
            score = -0.4
        else:
            status = 'neutral'
            score = 0
        
        return {
            'k_value': float(stoch_k),
            'd_value': float(stoch_d),
            'status': status,
            'score': score
        }

    def check_momentum_divergence(self, df: pd.DataFrame) -> Dict:
        """檢查動量背離"""
        if len(df) < 20:
            return {'divergence': 'insufficient_data', 'score': 0}
        
        # 取最近20天數據
        recent = df.iloc[-20:]
        
        # 價格高低點
        price_high_idx = recent['Close'].idxmax()
        price_low_idx = recent['Close'].idxmin()
        
        # RSI高低點
        rsi_high_idx = recent['RSI'].idxmax()
        rsi_low_idx = recent['RSI'].idxmin()
        
        divergence_score = 0
        divergence_type = 'none'
        
        # 頂背離檢查（價格創新高，RSI未創新高）
        if (price_high_idx > rsi_high_idx and 
            recent.loc[price_high_idx, 'Close'] > recent.loc[rsi_high_idx, 'Close'] and
            recent.loc[price_high_idx, 'RSI'] < recent.loc[rsi_high_idx, 'RSI']):
            divergence_type = 'bearish_divergence'
            divergence_score = -0.6
        
        # 底背離檢查（價格創新低，RSI未創新低）
        elif (price_low_idx > rsi_low_idx and 
              recent.loc[price_low_idx, 'Close'] < recent.loc[rsi_low_idx, 'Close'] and
              recent.loc[price_low_idx, 'RSI'] > recent.loc[rsi_low_idx, 'RSI']):
            divergence_type = 'bullish_divergence'
            divergence_score = 0.6
        
        return {
            'divergence': divergence_type,
            'score': divergence_score
        }

    def calculate_momentum_score(self, analysis: Dict) -> float:
        """計算動量綜合評分"""
        scores = [
            analysis['rsi_analysis']['score'] * 0.35,
            analysis['macd_analysis']['score'] * 0.35,
            analysis['stochastic_analysis']['score'] * 0.2,
            analysis['momentum_divergence']['score'] * 0.1
        ]
        
        return sum(scores)

    def analyze_volume(self, data: pd.DataFrame) -> Dict:
        """成交量分析"""
        df = data.copy()
        
        # 計算成交量指標
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        df['OBV'] = talib.OBV(df['Close'], df['Volume'])
        
        # VWAP計算
        df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
        
        latest = df.iloc[-1]
        recent = df.iloc[-10:]
        
        analysis = {
            'volume_trend': self.analyze_volume_trend(recent),
            'volume_confirmation': self.check_volume_confirmation(df),
            'obv_analysis': self.analyze_obv(recent),
            'vwap_analysis': self.analyze_vwap(latest),
            'volume_score': 0
        }
        
        # 計算成交量評分
        analysis['volume_score'] = self.calculate_volume_score(analysis)
        
        return analysis

    def analyze_volume_trend(self, recent: pd.DataFrame) -> Dict:
        """分析成交量趨勢"""
        volume_ma_trend = recent['Volume_MA'].iloc[-1] - recent['Volume_MA'].iloc[-5]
        current_volume_ratio = recent['Volume_Ratio'].iloc[-1]
        avg_volume_ratio = recent['Volume_Ratio'].mean()
        
        if current_volume_ratio > 1.5:
            trend_status = 'high_volume'
            score = 0.6
        elif current_volume_ratio > 1.2:
            trend_status = 'above_average'
            score = 0.3
        elif current_volume_ratio < 0.7:
            trend_status = 'low_volume'
            score = -0.3
        else:
            trend_status = 'normal'
            score = 0
        
        return {
            'current_ratio': float(current_volume_ratio),
            'average_ratio': float(avg_volume_ratio),
            'trend_status': trend_status,
            'ma_trend': 'rising' if volume_ma_trend > 0 else 'falling',
            'score': score
        }

    def check_volume_confirmation(self, df: pd.DataFrame) -> Dict:
        """檢查成交量確認"""
        if len(df) < 10:
            return {'confirmation': 'insufficient_data', 'score': 0}
        
        recent = df.iloc[-5:]
        price_change = recent['Close'].iloc[-1] - recent['Close'].iloc[0]
        volume_change = recent['Volume'].mean() - df['Volume'].iloc[-10:-5].mean()
        
        # 價漲量增
        if price_change > 0 and volume_change > 0:
            confirmation = 'bullish_confirmation'
            score = 0.6
        # 價跌量增
        elif price_change < 0 and volume_change > 0:
            confirmation = 'bearish_confirmation'
            score = -0.6
        # 價漲量減
        elif price_change > 0 and volume_change < 0:
            confirmation = 'weak_bullish'
            score = 0.2
        # 價跌量減
        elif price_change < 0 and volume_change < 0:
            confirmation = 'weak_bearish'
            score = -0.2
        else:
            confirmation = 'neutral'
            score = 0
        
        return {
            'confirmation': confirmation,
            'price_change_pct': (price_change / recent['Close'].iloc[0]) * 100,
            'volume_change_pct': (volume_change / df['Volume'].iloc[-10:-5].mean()) * 100,
            'score': score
        }

    def analyze_obv(self, recent: pd.DataFrame) -> Dict:
        """OBV分析"""
        if 'OBV' not in recent.columns or recent['OBV'].isna().all():
            return {'trend': 'insufficient_data', 'score': 0}
        
        obv_trend = recent['OBV'].iloc[-1] - recent['OBV'].iloc[-5]
        price_trend = recent['Close'].iloc[-1] - recent['Close'].iloc[-5]
        
        # OBV與價格一致性檢查
        if obv_trend > 0 and price_trend > 0:
            status = 'bullish_confirmation'
            score = 0.5
        elif obv_trend < 0 and price_trend < 0:
            status = 'bearish_confirmation'
            score = -0.5
        elif obv_trend > 0 and price_trend < 0:
            status = 'bullish_divergence'
            score = 0.3
        elif obv_trend < 0 and price_trend > 0:
            status = 'bearish_divergence'
            score = -0.3
        else:
            status = 'neutral'
            score = 0
        
        return {
            'obv_trend': obv_trend,
            'price_trend': price_trend,
            'status': status,
            'score': score
        }

    def analyze_vwap(self, latest: pd.Series) -> Dict:
        """VWAP分析"""
        if pd.isna(latest['VWAP']):
            return {'position': 'insufficient_data', 'score': 0}
        
        price = latest['Close']
        vwap = latest['VWAP']
        
        deviation_pct = (price / vwap - 1) * 100
        
        if deviation_pct > 2:
            position = 'above_vwap'
            score = 0.3
        elif deviation_pct < -2:
            position = 'below_vwap'
            score = -0.3
        else:
            position = 'near_vwap'
            score = 0
        
        return {
            'current_price': float(price),
            'vwap_value': float(vwap),
            'deviation_pct': round(deviation_pct, 2),
            'position': position,
            'score': score
        }

    def calculate_volume_score(self, analysis: Dict) -> float:
        """計算成交量綜合評分"""
        scores = [
            analysis['volume_trend']['score'] * 0.3,
            analysis['volume_confirmation']['score'] * 0.4,
            analysis['obv_analysis']['score'] * 0.2,
            analysis['vwap_analysis']['score'] * 0.1
        ]
        
        return sum(scores)

    def analyze_volatility(self, data: pd.DataFrame) -> Dict:
        """波動率分析"""
        df = data.copy()
        
        # 計算波動率指標
        df['BB_upper'], df['BB_middle'], df['BB_lower'] = talib.BBANDS(
            df['Close'], timeperiod=20, nbdevup=2, nbdevdn=2
        )
        df['ATR'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)
        df['KC_upper'], df['KC_middle'], df['KC_lower'] = self.calculate_keltner_channel(df)
        
        # 歷史波動率
        df['Returns'] = df['Close'].pct_change()
        df['HV_20'] = df['Returns'].rolling(window=20).std() * np.sqrt(252)
        
        latest = df.iloc[-1]
        recent = df.iloc[-20:]
        
        analysis = {
            'bollinger_bands': self.analyze_bollinger_bands(latest, recent),
            'atr_analysis': self.analyze_atr(latest, recent),
            'volatility_regime': self.identify_volatility_regime(recent),
            'volatility_score': 0
        }
        
        # 計算波動率評分
        analysis['volatility_score'] = self.calculate_volatility_score(analysis)
        
        return analysis

    def calculate_keltner_channel(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """計算Keltner通道"""
        ema_20 = talib.EMA(df['Close'], timeperiod=20)
        atr = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=20)
        
        kc_upper = ema_20 + (2 * atr)
        kc_middle = ema_20
        kc_lower = ema_20 - (2 * atr)
        
        return kc_upper, kc_middle, kc_lower

    def analyze_bollinger_bands(self, latest: pd.Series, recent: pd.DataFrame) -> Dict:
        """布林通道分析"""
        if pd.isna(latest['BB_upper']) or pd.isna(latest['BB_lower']):
            return {'position': 'insufficient_data', 'score': 0}
        
        price = latest['Close']
        bb_upper = latest['BB_upper']
        bb_lower = latest['BB_lower']
        bb_middle = latest['BB_middle']
        
        # 價格在布林通道中的位置
        bb_position = (price - bb_lower) / (bb_upper - bb_lower)
        
        if bb_position > 0.8:
            position = 'near_upper_band'
            score = -0.4  # 接近超買
        elif bb_position < 0.2:
            position = 'near_lower_band'
            score = 0.4   # 接近超賣
        else:
            position = 'middle_range'
            score = 0
        
        # 通道寬度分析
        band_width = (bb_upper - bb_lower) / bb_middle
        avg_width = ((recent['BB_upper'] - recent['BB_lower']) / recent['BB_middle']).mean()
        
        width_status = 'expanding' if band_width > avg_width * 1.1 else 'contracting'
        
        return {
            'price_position': round(bb_position, 3),
            'position': position,
            'band_width': round(band_width, 4),
            'width_status': width_status,
            'upper_band': float(bb_upper),
            'lower_band': float(bb_lower),
            'score': score
        }

    def analyze_atr(self, latest: pd.Series, recent: pd.DataFrame) -> Dict:
        """ATR波動率分析"""
        if pd.isna(latest['ATR']):
            return {'volatility': 'insufficient_data', 'score': 0}
        
        current_atr = latest['ATR']
        avg_atr = recent['ATR'].mean()
        atr_pct = (current_atr / latest['Close']) * 100
        
        # ATR水平判斷
        if current_atr > avg_atr * 1.5:
            volatility = 'high'
            score = -0.3  # 高波動性風險
        elif current_atr < avg_atr * 0.7:
            volatility = 'low'
            score = 0.2   # 低波動性機會
        else:
            volatility = 'normal'
            score = 0
        
        # ATR趨勢
        atr_trend = recent['ATR'].iloc[-5:].mean() - recent['ATR'].iloc[-10:-5].mean()
        trend_direction = 'rising' if atr_trend > 0 else 'falling'
        
        return {
            'current_atr': float(current_atr),
            'average_atr': float(avg_atr),
            'atr_percentage': round(atr_pct, 2),
            'volatility': volatility,
            'trend': trend_direction,
            'score': score
        }

    def identify_volatility_regime(self, recent: pd.DataFrame) -> Dict:
        """識別波動率制度"""
        if 'HV_20' not in recent.columns or recent['HV_20'].isna().all():
            return {'regime': 'unknown', 'score': 0}
        
        current_hv = recent['HV_20'].iloc[-1]
        avg_hv = recent['HV_20'].mean()
        
        if current_hv > avg_hv * 1.3:
            regime = 'high_volatility'
            score = -0.4
        elif current_hv < avg_hv * 0.7:
            regime = 'low_volatility'
            score = 0.3
        else:
            regime = 'normal_volatility'
            score = 0
        
        return {
            'regime': regime,
            'current_hv': round(float(current_hv), 4),
            'average_hv': round(float(avg_hv), 4),
            'score': score
        }

    def calculate_volatility_score(self, analysis: Dict) -> float:
        """計算波動率綜合評分"""
        scores = [
            analysis['bollinger_bands']['score'] * 0.4,
            analysis['atr_analysis']['score'] * 0.3,
            analysis['volatility_regime']['score'] * 0.3
        ]
        
        return sum(scores)

    def calculate_technical_score(self, analyses: Dict) -> Dict:
        """計算技術面綜合評分"""
        weighted_scores = {}
        total_score = 0
        
        for category, weight in self.analysis_weights.items():
            if category in analyses:
                category_score = analyses[category].get(f'{category}_score', 0)
                weighted_scores[category] = category_score * weight
                total_score += weighted_scores[category]
        
        # 正規化評分到 -10 到 10
        normalized_score = total_score * 10
        
        # 評級判斷
        if normalized_score > 6:
            rating = "強烈看多 🟢"
        elif normalized_score > 3:
            rating = "看多 🟢"
        elif normalized_score > 1:
            rating = "偏多 🟡"
        elif normalized_score > -1:
            rating = "中性 ⚪"
        elif normalized_score > -3:
            rating = "偏空 🟡"
        elif normalized_score > -6:
            rating = "看空 🔴"
        else:
            rating = "強烈看空 🔴"
        
        return {
            'total_score': round(normalized_score, 2),
            'weighted_scores': {k: round(v, 2) for k, v in weighted_scores.items()},
            'rating': rating,
            'confidence': min(abs(normalized_score) / 10, 1.0)
        }

    def integrate_with_strategy(self, technical_score: Dict, strategy_result: Dict) -> Dict:
        """整合技術分析與策略結果"""
        if 'final_recommendation' not in strategy_result:
            return {
                'integration_status': 'strategy_unavailable',
                'combined_score': technical_score['total_score'],
                'recommendation': 'based_on_technical_only'
            }
        
        strategy_rec = strategy_result['final_recommendation']
        
        if 'error' in strategy_rec:
            return {
                'integration_status': 'strategy_error',
                'combined_score': technical_score['total_score'],
                'recommendation': 'based_on_technical_only'
            }
        
        # 整合評分
        technical_weight = 0.4
        strategy_weight = 0.6
        
        strategy_score = 0
        if strategy_rec['position'] == 'LONG':
            strategy_score = strategy_rec.get('signal_strength', 0) * 10
        elif strategy_rec['position'] == 'SHORT':
            strategy_score = -strategy_rec.get('signal_strength', 0) * 10
        
        combined_score = (technical_score['total_score'] * technical_weight + 
                         strategy_score * strategy_weight)
        
        # 一致性檢查
        consistency = self.check_consistency(technical_score, strategy_rec)
        
        return {
            'integration_status': 'success',
            'technical_score': technical_score['total_score'],
            'strategy_score': round(strategy_score, 2),
            'combined_score': round(combined_score, 2),
            'consistency': consistency,
            'final_rating': self.get_combined_rating(combined_score),
            'confidence': (technical_score['confidence'] + strategy_rec.get('confidence', 0)) / 2
        }

    def check_consistency(self, technical_score: Dict, strategy_rec: Dict) -> Dict:
        """檢查技術分析與策略的一致性"""
        tech_score = technical_score['total_score']
        strategy_position = strategy_rec['position']
        
        # 判斷技術面傾向
        if tech_score > 1:
            tech_bias = 'bullish'
        elif tech_score < -1:
            tech_bias = 'bearish'
        else:
            tech_bias = 'neutral'
        
        # 策略傾向
        if strategy_position == 'LONG':
            strategy_bias = 'bullish'
        elif strategy_position == 'SHORT':
            strategy_bias = 'bearish'
        else:
            strategy_bias = 'neutral'
        
        # 一致性判斷
        if tech_bias == strategy_bias:
            consistency = 'high'
            consistency_score = 0.8
        elif tech_bias == 'neutral' or strategy_bias == 'neutral':
            consistency = 'moderate'
            consistency_score = 0.5
        else:
            consistency = 'low'
            consistency_score = 0.2
        
        return {
            'level': consistency,
            'score': consistency_score,
            'technical_bias': tech_bias,
            'strategy_bias': strategy_bias
        }

    def get_combined_rating(self, combined_score: float) -> str:
        """獲取組合評級"""
        if combined_score > 7:
            return "極度看多 🚀"
        elif combined_score > 4:
            return "強烈看多 🟢"
        elif combined_score > 2:
            return "看多 🟢"
        elif combined_score > 0.5:
            return "偏多 🟡"
        elif combined_score > -0.5:
            return "中性 ⚪"
        elif combined_score > -2:
            return "偏空 🟡"
        elif combined_score > -4:
            return "看空 🔴"
        elif combined_score > -7:
            return "強烈看空 🔴"
        else:
            return "極度看空 💥"

    def assess_risk_level(self, data: pd.DataFrame, volatility_analysis: Dict) -> Dict:
        """評估風險等級"""
        risk_factors = []
        risk_score = 0
        
        # 波動率風險
        vol_score = volatility_analysis.get('volatility_score', 0)
        if vol_score < -0.3:
            risk_factors.append("高波動率")
            risk_score += 2
        
        # 價格風險（相對高低點位置）
        recent_high = data['High'].rolling(window=52).max().iloc[-1]
        recent_low = data['Low'].rolling(window=52).min().iloc[-1]
        current_price = data['Close'].iloc[-1]
        
        price_position = (current_price - recent_low) / (recent_high - recent_low)
        
        if price_position > 0.9:
            risk_factors.append("接近年度高點")
            risk_score += 1
        elif price_position < 0.1:
            risk_factors.append("接近年度低點")
            risk_score += 1
        
        # 流動性風險（成交量）
        recent_volume = data['Volume'].iloc[-5:].mean()
        avg_volume = data['Volume'].rolling(window=50).mean().iloc[-1]
        
        if recent_volume < avg_volume * 0.5:
            risk_factors.append("成交量不足")
            risk_score += 1
        
        # 風險等級判斷
        if risk_score >= 4:
            risk_level = "極高風險 ⚫"
            level_score = 10
        elif risk_score >= 3:
            risk_level = "高風險 🔴"
            level_score = 8
        elif risk_score >= 2:
            risk_level = "中風險 🟠"
            level_score = 6
        elif risk_score >= 1:
            risk_level = "中低風險 🟡"
            level_score = 4
        else:
            risk_level = "低風險 🟢"
            level_score = 2
        
        return {
            'risk_level': risk_level,
            'risk_score': level_score,
            'risk_factors': risk_factors,
            'price_position': round(price_position, 3),
            'volume_health': 'normal' if recent_volume >= avg_volume * 0.8 else 'weak',
            'volatility_status': volatility_analysis.get('volatility_regime', {}).get('regime', 'unknown')
        }

    def generate_investment_advice(self, integrated_analysis: Dict, risk_assessment: Dict) -> Dict:
        """生成投資建議"""
        combined_score = integrated_analysis.get('combined_score', 0)
        risk_score = risk_assessment.get('risk_score', 5)
        consistency = integrated_analysis.get('consistency', {}).get('level', 'low')
        
        advice = {
            'primary_action': '',
            'position_sizing': '',
            'time_horizon': '',
            'key_points': [],
            'risk_warnings': [],
            'stop_loss_suggestion': '',
            'target_suggestion': ''
        }
        
        # 主要操作建議
        if combined_score > 4 and consistency == 'high':
            advice['primary_action'] = "積極買入"
            advice['position_sizing'] = "標準倉位 (60-80%)"
            advice['time_horizon'] = "中長期持有 (1-3個月)"
        elif combined_score > 2:
            advice['primary_action'] = "逢低買入"
            advice['position_sizing'] = "適中倉位 (40-60%)"
            advice['time_horizon'] = "短中期操作 (2-6週)"
        elif combined_score > 0.5:
            advice['primary_action'] = "小幅買入"
            advice['position_sizing'] = "輕倉試水 (20-40%)"
            advice['time_horizon'] = "短期操作 (1-2週)"
        elif combined_score < -4 and consistency == 'high':
            advice['primary_action'] = "積極賣出"
            advice['position_sizing'] = "減倉至最低"
            advice['time_horizon'] = "立即執行"
        elif combined_score < -2:
            advice['primary_action'] = "逢高減倉"
            advice['position_sizing'] = "減少倉位"
            advice['time_horizon'] = "短期調整"
        else:
            advice['primary_action'] = "觀望等待"
            advice['position_sizing'] = "保持現狀"
            advice['time_horizon'] = "等待明確信號"
        
        # 風險調整
        if risk_score >= 8:
            advice['risk_warnings'].append("⚠️ 高風險環境，建議降低倉位")
            if "買入" in advice['primary_action']:
                advice['position_sizing'] = "謹慎輕倉 (10-30%)"
        
        if risk_score <= 3:
            advice['key_points'].append("✅ 低風險環境，適合佈局")
        
        # 一致性調整
        if consistency == 'low':
            advice['risk_warnings'].append("⚠️ 技術面與策略面信號不一致，建議謹慎")
        
        return advice

    def identify_market_regime(self, data: pd.DataFrame) -> Dict:
        """識別市場制度"""
        if len(data) < 50:
            return {'regime': 'insufficient_data'}
        
        # 趨勢強度
        sma_20 = talib.SMA(data['Close'], timeperiod=20)
        sma_50 = talib.SMA(data['Close'], timeperiod=50)
        
        recent_trend = (sma_20.iloc[-1] - sma_20.iloc[-20]) / sma_20.iloc[-20]
        
        # 波動率水平
        returns = data['Close'].pct_change()
        current_vol = returns.iloc[-20:].std() * np.sqrt(252)
        long_vol = returns.std() * np.sqrt(252)
        
        # 制度識別
        if abs(recent_trend) < 0.05 and current_vol < long_vol * 0.8:
            regime = "低波動盤整"
            regime_score = 3
        elif abs(recent_trend) < 0.05 and current_vol > long_vol * 1.2:
            regime = "高波動震盪"
            regime_score = 7
        elif recent_trend > 0.1:
            if current_vol < long_vol:
                regime = "穩健上漲"
                regime_score = 2
            else:
                regime = "激烈上漲"
                regime_score = 8
        elif recent_trend < -0.1:
            if current_vol < long_vol:
                regime = "穩定下跌"
                regime_score = 6
            else:
                regime = "恐慌下跌"
                regime_score = 9
        else:
            regime = "一般市況"
            regime_score = 5
        
        return {
            'regime': regime,
            'regime_score': regime_score,
            'trend_strength': round(recent_trend, 4),
            'volatility_ratio': round(current_vol / long_vol, 2)
        }

    def calculate_key_levels(self, data: pd.DataFrame) -> Dict:
        """計算關鍵價位"""
        if len(data) < 20:
            return {'levels': 'insufficient_data'}
        
        current_price = data['Close'].iloc[-1]
        
        # 支撐阻力位計算
        highs = data['High'].rolling(window=10).max()
        lows = data['Low'].rolling(window=10).min()
        
        # 近期重要高低點
        resistance_levels = []
        support_levels = []
        
        for i in range(len(data)-20, len(data)):
            if i > 10 and i < len(data) - 10:
                # 局部高點
                if (data['High'].iloc[i] == highs.iloc[i] and 
                    data['High'].iloc[i] > data['High'].iloc[i-5:i+5].mean() * 1.02):
                    resistance_levels.append(data['High'].iloc[i])
                
                # 局部低點
                if (data['Low'].iloc[i] == lows.iloc[i] and 
                    data['Low'].iloc[i] < data['Low'].iloc[i-5:i+5].mean() * 0.98):
                    support_levels.append(data['Low'].iloc[i])
        
        # 移動平均線作為動態支撐阻力
        sma_20 = talib.SMA(data['Close'], timeperiod=20).iloc[-1]
        sma_50 = talib.SMA(data['Close'], timeperiod=50).iloc[-1]
        
        # 整理關鍵位
        key_resistance = sorted(set(resistance_levels), reverse=True)[:3]
        key_support = sorted(set(support_levels), reverse=True)[:3]
        
        return {
            'current_price': float(current_price),
            'key_resistance': [float(x) for x in key_resistance],
            'key_support': [float(x) for x in key_support],
            'sma_20': float(sma_20) if not pd.isna(sma_20) else None,
            'sma_50': float(sma_50) if not pd.isna(sma_50) else None,
            'nearest_resistance': min(key_resistance) if key_resistance else None,
            'nearest_support': max(key_support) if key_support else None
        }

    def save_analysis_result(self, result: Dict, output_path: str = None):
        """保存分析結果"""
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"data/analysis/market_analysis_{result['symbol']}_{timestamp}.json"
        
        try:
            import os
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"市場分析結果已保存: {output_path}")
            
        except Exception as e:
            logger.error(f"分析結果保存失敗: {e}")

def main():
    """主程序示例"""
    import argparse
    import sys
    import os

    # 添加項目根目錄到路徑，以便導入其他模組
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    parser = argparse.ArgumentParser(description='市場解析師 - 技術分析引擎')
    parser.add_argument('--symbol', type=str, required=True, help='分析標的')
    parser.add_argument('--market', type=str, choices=['us', 'tw'], default='us', help='市場類型')
    parser.add_argument('--depth', type=str, choices=['basic', 'comprehensive'], 
                       default='comprehensive', help='分析深度')
    parser.add_argument('--period', type=str, default='6mo', help='分析時間範圍')
    parser.add_argument('--strategy-result', type=str, help='策略分析結果JSON文件路徑')

    args = parser.parse_args()

    # 初始化市場解析師
    analyst = MarketIntelligenceAnalyst()

    # 載入策略結果（如果有）
    strategy_result = {}
    if args.strategy_result and os.path.exists(args.strategy_result):
        try:
            with open(args.strategy_result, 'r', encoding='utf-8') as f:
                strategy_result = json.load(f)
            logger.info(f"已載入策略結果: {args.strategy_result}")
        except Exception as e:
            logger.warning(f"策略結果載入失敗: {e}")

    # 執行市場分析
    logger.info(f"開始分析: {args.symbol} ({args.market})")
    result = analyst.comprehensive_analysis(
        symbol=args.symbol,
        strategy_result=strategy_result,
        period=args.period
    )

    # 保存結果
    analyst.save_analysis_result(result)

    # 輸出摘要
    if 'error' not in result:
        print(f"\n=== {args.symbol} 市場分析摘要 ===")
        print(f"技術評分: {result['technical_score']['total_score']}")
        print(f"技術評級: {result['technical_score']['rating']}")
        
        if 'integrated_analysis' in result:
            integrated = result['integrated_analysis']
            print(f"綜合評分: {integrated.get('combined_score', 'N/A')}")
            print(f"綜合評級: {integrated.get('final_rating', 'N/A')}")
            print(f"信號一致性: {integrated.get('consistency', {}).get('level', 'N/A')}")
        
        print(f"風險等級: {result['risk_assessment']['risk_level']}")
        print(f"市場制度: {result['market_regime']['regime']}")
        
        if result['investment_advice']['primary_action']:
            print(f"主要建議: {result['investment_advice']['primary_action']}")
            print(f"倉位建議: {result['investment_advice']['position_sizing']}")
    else:
        print(f"分析失敗: {result['error']}")

if __name__ == "__main__":
    main()