import pandas as pd
import ta
from loguru import logger

class MarketAnalyst:
    def __init__(self, config_manager):
        self.config = config_manager
        self.min_data_length = self.config.get('strategy_params', {}).get('technical_params', {}).get('min_data_length_rsi_sma', 20)

    def analyze_market(self, symbol, timeframe='daily'):
        file_path = f"{self.config['data_paths']['market']}/{timeframe}_{symbol.replace('^', '').replace('.', '_')}.csv"
        if not os.path.exists(file_path):
            logger.error(f"{symbol} {timeframe} 數據檔案不存在: {file_path}")
            return {
                'trend': 'NEUTRAL',
                'volatility': 0.0,
                'technical_indicators': {},
                'report': '無數據可分析'
            }
        
        try:
            df = pd.read_csv(file_path)
            df['date'] = pd.to_datetime(df['date'])
            if df.empty or len(df) < self.min_data_length:
                logger.error(f"{symbol} {timeframe} 數據不足: 實際 {len(df)} 筆，需 {self.min_data_length} 筆")
                return {
                    'trend': 'NEUTRAL',
                    'volatility': 0.0,
                    'technical_indicators': {},
                    'report': '數據不足'
                }
            
            # 技術指標計算
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=self.config['strategy_params']['technical_params']['rsi_window']).rsi()
            df['macd'] = ta.trend.MACD(df['close'], 
                                      window_fast=self.config['strategy_params']['technical_params']['macd_fast'],
                                      window_slow=self.config['strategy_params']['technical_params']['macd_slow'],
                                      window_sign=self.config['strategy_params']['technical_params']['macd_signal']).macd()
            df['bollinger_hband'] = ta.volatility.BollingerBands(df['close']).bollinger_hband()
            df['bollinger_lband'] = ta.volatility.BollingerBands(df['close']).bollinger_lband()
            df['sma_50'] = ta.trend.SMAIndicator(df['close'], window=50).sma_indicator()
            df['sma_200'] = ta.trend.SMAIndicator(df['close'], window=200).sma_indicator()
            
            # 趨勢分析：黃金交叉/死亡交叉
            trend = 'NEUTRAL'
            if df['sma_50'].iloc[-1] > df['sma_200'].iloc[-1]:
                trend = 'BULLISH'  # 看漲
            elif df['sma_50'].iloc[-1] < df['sma_200'].iloc[-1]:
                trend = 'BEARISH'  # 看跌
            
            # 波動性：最近 20 期的標準差
            volatility = df['close'].pct_change().rolling(20).std().iloc[-1] * 100 if 'close' in df else 0.0
            volatility = volatility if not pd.isna(volatility) else 0.0
            
            # 指標摘要
            indicators = {
                'rsi': float(df['rsi'].iloc[-1]) if not pd.isna(df['rsi'].iloc[-1]) else 0.0,
                'macd': float(df['macd'].iloc[-1]) if not pd.isna(df['macd'].iloc[-1]) else 0.0,
                'bollinger': {
                    'high': float(df['bollinger_hband'].iloc[-1]) if not pd.isna(df['bollinger_hband'].iloc[-1]) else 0.0,
                    'low': float(df['bollinger_lband'].iloc[-1]) if not pd.isna(df['bollinger_lband'].iloc[-1]) else 0.0
                }
            }
            
            # 生成報告
            report = (f"{symbol} 市場分析：趨勢 {trend}，波動性 {volatility:.2f}%，"
                      f"RSI {indicators['rsi']:.2f}，MACD {indicators['macd']:.2f}。")
            
            logger.info(f"{symbol} 市場分析完成")
            return {
                'trend': trend,
                'volatility': volatility,
                'technical_indicators': indicators,
                'report': report
            }
        except Exception as e:
            logger.error(f"{symbol} 市場分析失敗: {str(e)}")
            return {
                'trend': 'NEUTRAL',
                'volatility': 0.0,
                'technical_indicators': {},
                'report': '分析失敗'
            }
