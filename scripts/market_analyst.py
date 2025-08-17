import pandas as pd
import json
import os
from datetime import datetime
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    """載入配置檔案 config.json"""
    config_file = 'config.json'
    if not os.path.exists(config_file):
        logger.error(f"缺少配置檔案: {config_file}")
        raise FileNotFoundError(f"缺少配置檔案: {config_file}")
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('symbols', [])
    except json.JSONDecodeError as e:
        logger.error(f"配置檔案解析失敗: {e}")
        raise ValueError(f"配置檔案解析失敗: {e}")

def load_data(symbol):
    """載入每日數據和策略結果"""
    data_path = os.path.join('data', f'daily_{symbol}.csv')
    strategy_path = os.path.join('data', f'strategy_best_{symbol}.json')
    if not os.path.exists(data_path):
        logger.error(f"缺少 {data_path}")
        return None, None
    if not os.path.exists(strategy_path):
        logger.error(f"缺少 {strategy_path}")
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

def analyze_market(df, strategy):
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

    # 基礎建議
    if pct_change > 1.0 and volume_change > 1.2:  # 價格上漲且成交量增加
        recommendation = '買入'
        position_size = min(0.5, 0.1 + (strategy.get('return', 0) / 20))  # 勝率越高倉位越高
    elif pct_change < -1.0 or volume_change < 0.8:  # 價格下跌或成交量縮減
        recommendation = '賣出'
        position_size = 0.0
    else:
        recommendation = '持倉'
        position_size = strategy.get('position_size', 0.0)

    # 目標價和停損價
    target_price = latest['Close'] * 1.02 if recommendation == '買入' else None
    stop_loss = latest['Close'] * 0.98 if recommendation in ['買入', '持倉'] else None

    # 風險評估
    risk_note = f"漲跌: {pct_change:.2f}%, 成交量變化: {volume_change:.2f}x"

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
    symbols = load_config()
    for symbol in symbols:
        df, strategy = load_data(symbol)
        if df is not None and strategy is not None:
            analysis = analyze_market(df, strategy)
            save_analysis(analysis, symbol)
        else:
            logger.warning(f"跳過 {symbol} 分析，因數據或策略缺失")

if __name__ == '__main__':
    main()
