import pandas as pd
import json
import os
from datetime import datetime
import logging

# 設定日誌
logging.basicConfig(filename='logs/market_analyst.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    """載入 config.json 配置文件"""
    config_file = 'config.json'
    if not os.path.exists(config_file):
        logger.error(f"缺少配置檔案: {config_file}")
        raise FileNotFoundError(f"缺少配置檔案: {config_file}")
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        indicators = config.get('indicators', {'MACD': {'fast': 12, 'slow': 26, 'signal': 9}, 'RSI': {'period': 14}})
        return config.get('symbols', []), indicators
    except json.JSONDecodeError as e:
        logger.error(f"配置檔案解析失敗: {e}")
        raise ValueError(f"配置檔案解析失敗: {e}")

def load_data(symbol):
    """載入每日數據和最佳策略結果"""
    data_path = os.path.join('data', f'daily_{symbol}.csv')
    strategy_path = os.path.join('data', f'strategy_best_{symbol}.json')
    if not os.path.exists(data_path) or not os.path.exists(strategy_path):
        logger.error(f"缺少 {data_path} 或 {strategy_path}")
        return None, None
    try:
        df = pd.read_csv(data_path)
        df['Date'] = pd.to_datetime(df['Date'])
        with open(strategy_path, 'r', encoding='utf-8') as f:
            strategy = json.load(f)
        return df, strategy
    except Exception as e:
        logger.error(f"載入 {symbol} 數據或策略失敗: {e}")
        return None, None

def calculate_macd(df, fast=12, slow=26, signal=9):
    """計算 MACD 指標"""
    exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd.iloc[-1], signal_line.iloc[-1]

def calculate_rsi(df, period=14):
    """計算 RSI 指標（可選）"""
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss if loss != 0 else gain
    rsi = 100 - (100 / (1 + rs)) if loss != 0 else 100
    return rsi.iloc[-1] if not rsi.empty else 0

def analyze_market(df, strategy, indicators):
    """分析市場趨勢並提供建議"""
    if df is None or strategy is None:
        logger.warning("數據或策略缺失，返回預設建議")
        return {
            'symbol': symbol,
            'recommendation': '持倉',
            'position_size': 0.0,
            'target_price': None,
            'stop_loss': None,
            'risk_note': '數據不足，建議檢查'
        }

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    pct_change = ((latest['Close'] - prev['Close']) / prev['Close'] * 100) if prev['Close'] else 0.0
    volume_change = (latest['Volume'] / prev['Volume']) if prev['Volume'] else 1.0
    macd, signal = calculate_macd(df, **indicators.get('MACD', {}))
    rsi = calculate_rsi(df, **indicators.get('RSI', {}))
    trend_5d = df['Close'].pct_change(periods=5).iloc[-1] * 100 if len(df) >= 5 else 0.0

    logger.info(f"輸入摘要 - {symbol}: 當日漲跌 {pct_change:.2f}%, 成交量變化 {volume_change:.2f}x, MACD {macd:.2f}/{signal:.2f}, RSI {rsi:.2f}, 5日趨勢 {trend_5d:.2f}%")

    # 歷史趨勢比較
    is_trend_up = trend_5d > 0
    is_recent_up = pct_change > 0

    # 基礎建議
    if pct_change > 1.0 and volume_change > 1.2 and macd > signal and rsi > 50 and (is_trend_up or is_recent_up):
        recommendation = '買入'
        position_size = min(0.5, 0.1 + (strategy.get('return', 0) / 20))
    elif pct_change < -1.0 or volume_change < 0.8 or macd < signal or rsi < 30 or (not is_trend_up and not is_recent_up):
        recommendation = '賣出'
        position_size = 0.0
    else:
        recommendation = '持倉'
        position_size = strategy.get('position_size', 0.0)

    # 目標價和停損價
    target_price = latest['Close'] * 1.02 if recommendation == '買入' else None
    stop_loss = latest['Close'] * 0.98 if recommendation in ['買入', '持倉'] else None

    # 風險評估與歷史比較
    risk_note = f"漲跌: {pct_change:.2f}%, 成交量變化: {volume_change:.2f}x, MACD: {macd:.2f}/{signal:.2f}, RSI: {rsi:.2f}, 5日趨勢: {trend_5d:.2f}%"

    logger.info(f"計算過程 - {symbol}: 建議 {recommendation}, 倉位 {position_size:.2f}, 目標價 {target_price}, 停損 {stop_loss}, 風險: {risk_note}")

    return {
        'symbol': symbol,
        'recommendation': recommendation,
        'position_size': position_size,
        'target_price': target_price,
        'stop_loss': stop_loss,
        'risk_note': risk_note
    }

def save_analysis(analysis, symbol):
    """保存分析結果"""
    output_path = os.path.join('data', f'market_analysis_{symbol}.json')
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        logger.info(f"分析結果保存至 {output_path}")
    except Exception as e:
        logger.error(f"保存 {symbol} 分析結果失敗: {e}")

def main():
    """主函數，執行市場分析"""
    symbols, indicators = load_config()
    for symbol in symbols:
        df, strategy = load_data(symbol)
        if df is not None and strategy is not None:
            analysis = analyze_market(df, strategy, indicators)
            save_analysis(analysis, symbol)
        else:
            logger.warning(f"跳過 {symbol} 分析，因數據或策略缺失")

if __name__ == '__main__':
    # 支援單一符號分析
    import sys
    if len(sys.argv) > 1:
        symbols = [sys.argv[1]]
    main()
