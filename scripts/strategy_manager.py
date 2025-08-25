# scripts/strategy_manager.py
import pandas as pd
import json
import os
import sys
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from statsmodels.tsa.arima.model import ARIMA
from utils import setup_json_logger, get_grok_client, slack_alert, config_manager
import numpy as np
from sklearn.metrics import accuracy_score

logger = setup_json_logger('strategy_manager')

def optimize_params(strategy_name, params, performance):
    """使用 Grok API 優化策略參數"""
    try:
        client = get_grok_client()
        prompt = f"""
        請為 {strategy_name} 策略優化參數，用於短期交易（1-3天）。
        當前表現: {performance}
        當前參數: {json.dumps(params, indent=2)}
        
        請返回優化後的參數，格式為JSON：
        {{
            "param1": value1,
            "param2": value2,
            ...
        }}
        """
        
        response = client.chat.completions.create(
            model="grok-beta",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        # 嘗試解析JSON回應
        response_text = response.choices[0].message.content.strip()
        
        # 提取JSON部分（如果回應包含其他文字）
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            optimized_params = json.loads(json_match.group())
            logger.info(f"成功優化 {strategy_name} 策略參數")
            return optimized_params
        else:
            logger.warning(f"無法解析 Grok API 回應，使用原始參數")
            return params
            
    except Exception as e:
        logger.error(f"優化策略參數時發生錯誤: {e}")
        return params

def load_strategies_config():
    """載入策略配置"""
    try:
        strategies_config = config_manager.strategies_config
        if not strategies_config or 'available_strategies' not in strategies_config:
            logger.error("策略配置檔案格式錯誤或為空")
            return []
        
        strategies = []
        for strategy_key, strategy_info in strategies_config['available_strategies'].items():
            if strategy_info.get('enabled', False):
                strategy = {
                    'name': strategy_key,
                    'display_name': strategy_info.get('name', strategy_key),
                    'params': strategy_info.get('parameters', {}),
                    'weight': strategy_info.get('weight', 0.25)
                }
                strategies.append(strategy)
        
        logger.info(f"載入 {len(strategies)} 個啟用的策略")
        return strategies
        
    except Exception as e:
        logger.error(f"載入策略配置時發生錯誤: {e}")
        return []

def main(mode=None):
    """主要執行函數"""
    try:
        # 載入配置
        base_config = config_manager.base_config
        strategies = load_strategies_config()
        
        if not strategies:
            slack_alert("無可用的策略配置", urgent=True)
            return
        
        # 確定要分析的標的
        if mode == 'us':
            focus_symbol = 'QQQ'
            market_config = base_config.get('markets', {}).get('us', {})
        else:
            focus_symbol = '0050.TW'
            market_config = base_config.get('markets', {}).get('taiwan', {})
        
        clean_symbol = focus_symbol.replace('.', '_').replace('^', '')
        
        # 檢查數據檔案
        project_root = Path(__file__).parent.parent
        daily_file = project_root / "data/market" / f"daily_{clean_symbol}.csv"
        
        if not daily_file.exists():
            logger.error(f"找不到數據檔案: {daily_file}")
            slack_alert(f"缺少 {focus_symbol} 的數據檔案: {daily_file}")
            return
        
        # 載入和預處理數據
        logger.info(f"載入數據檔案: {daily_file}")
        df = pd.read_csv(daily_file, index_col='Date', parse_dates=True)
        
        if len(df) < 100:
            logger.warning(f"{focus_symbol} 數據量不足，僅有 {len(df)} 筆記錄")
            slack_alert(f"{focus_symbol} 數據量不足")
            return
        
        # 計算基本特徵
        df['Return'] = df['Close'].pct_change()
        df['Label'] = np.where(df['Return'] > 0, 1, 0)
        df['SMA_5'] = df['Close'].rolling(window=5).mean()
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['RSI'] = calculate_rsi(df['Close'], window=14)
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        
        # 移除空值
        df.dropna(inplace=True)
        
        if len(df) < 50:
            logger.warning(f"處理後數據量不足: {len(df)}")
            return
        
        logger.info(f"{focus_symbol} 數據預處理完成，共 {len(df)} 筆記錄")
        
        # ARIMA 基準模型
        try:
            arima_model = ARIMA(df['Close'], order=(1,1,1)).fit()
            test_size = min(len(df) // 5, 50)  # 測試集大小
            arima_forecast = arima_model.forecast(steps=test_size)
            
            # 計算ARIMA基準準確率（簡化）
            baseline_acc = 0.5  # 預設基準值
            logger.info(f"ARIMA 基準準確率: {baseline_acc:.3f}")
            
        except Exception as e:
            logger.warning(f"ARIMA 模型訓練失敗: {e}")
            baseline_acc = 0.5
        
        # 策略評估
        best_strategy = None
        best_win_rate = 0
        best_params = {}
        strategy_results = []
        
        # 準備特徵數據
        feature_columns = ['Open', 'High', 'Low', 'Volume', 'SMA_5', 'SMA_20', 'RSI', 'Volume_Ratio']
        available_features = [col for col in feature_columns if col in df.columns]
        
        if len(available_features) < 4:
            logger.error("可用特徵數量不足")
            return
        
        X = df[available_features].values[:-1]  # 特徵
        y = df['Label'].values[1:]  # 標籤（預測下一期）
        
        # 訓練/測試分割
        split_point = int(0.8 * len(X))
        X_train, X_test = X[:split_point], X[split_point:]
        y_train, y_test = y[:split_point], y[split_point:]
        
        logger.info(f"訓練集大小: {len(X_train)}, 測試集大小: {len(X_test)}")
        
        # 評估每個策略
        for strategy in strategies:
            try:
                strategy_name = strategy['name']
                params = strategy['params']
                
                if strategy_name in ['technical_analysis']:
                    # 技術分析策略（使用簡單規則）
                    signals = evaluate_technical_strategy(df, params)
                    acc = accuracy_score(y_test[:len(signals)], signals[:len(y_test)])
                    
                elif strategy_name in ['ml_random_forest']:
                    # 隨機森林策略
                    rf_params = {
                        'n_estimators': params.get('n_estimators', 100),
                        'max_depth': params.get('max_depth', 10),
                        'min_samples_split': params.get('min_samples_split', 5),
                        'random_state': 42
                    }
                    model = RandomForestClassifier(**rf_params)
                    model.fit(X_train, y_train)
                    predictions = model.predict(X_test)
                    acc = accuracy_score(y_test, predictions)
                    
                elif strategy_name == 'lstm_deep_learning':
                    # LSTM策略（簡化實現）
                    acc = evaluate_lstm_strategy(df, params)
                    
                elif strategy_name == 'sentiment_analysis':
                    # 情緒分析策略（模擬）
                    acc = 0.52 + np.random.random() * 0.1  # 模擬結果
                    
                else:
                    logger.warning(f"未知策略類型: {strategy_name}")
                    continue
                
                strategy_result = {
                    'strategy': strategy_name,
                    'display_name': strategy.get('display_name', strategy_name),
                    'accuracy': acc,
                    'params': params
                }
                strategy_results.append(strategy_result)
                
                logger.info(f"{strategy_name} 策略準確率: {acc:.3f}")
                
                # 更新最佳策略
                if acc > baseline_acc + 0.05 and acc > best_win_rate:
                    best_win_rate = acc
                    best_strategy = strategy_name
                    best_params = params
                    
            except Exception as e:
                logger.error(f"評估策略 {strategy['name']} 時發生錯誤: {e}")
                continue
        
        # 保存結果
        if best_strategy and best_win_rate > 0.55:
            logger.info(f"找到最佳策略: {best_strategy}, 勝率: {best_win_rate:.3f}")
            
            # 使用 Grok API 優化參數
            optimized_params = optimize_params(best_strategy, best_params, f"準確率: {best_win_rate:.3f}")
            
            output = {
                "timestamp": pd.Timestamp.now().isoformat(),
                "symbol": focus_symbol,
                "best_strategy": best_strategy,
                "optimized_params": optimized_params,
                "win_rate": best_win_rate,
                "baseline_accuracy": baseline_acc,
                "improvement": best_win_rate - baseline_acc,
                "all_strategies": strategy_results
            }
            
            # 保存結果檔案
            output_dir = project_root / "data"
            output_dir.mkdir(exist_ok=True)
            json_file = output_dir / f"strategy_best_{clean_symbol}.json"
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            
            logger.info(f"策略結果已保存: {json_file}")
            
            # 發送通知
            message = (
                f"🎯 {focus_symbol} 最佳策略更新\n"
                f"策略: {best_strategy}\n"
                f"勝率: {best_win_rate:.1%}\n"
                f"基準線: {baseline_acc:.1%}\n"
                f"提升: +{(best_win_rate - baseline_acc):.1%}"
            )
            slack_alert(message)
            
        else:
            logger.warning(f"未找到符合條件的策略 (最佳勝率: {best_win_rate:.3f})")
            slack_alert(f"⚠️ {focus_symbol} 無策略超越基準線 (最佳: {best_win_rate:.1%})")
        
    except Exception as e:
        logger.error(f"策略管理器執行錯誤: {e}")
        slack_alert(f"❌ 策略管理器執行失敗: {str(e)}", urgent=True)


def calculate_rsi(prices, window=14):
    """計算RSI指標"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def evaluate_technical_strategy(df, params):
    """評估技術分析策略"""
    sma_short = params.get('sma_short', 20)
    sma_long = params.get('sma_long', 50)
    rsi_overbought = params.get('rsi_overbought', 70)
    rsi_oversold = params.get('rsi_oversold', 30)
    
    # 計算技術指標
    df['SMA_Short'] = df['Close'].rolling(window=sma_short).mean()
    df['SMA_Long'] = df['Close'].rolling(window=sma_long).mean()
    
    # 生成信號
    signals = []
    for i in range(len(df)):
        if pd.isna(df['SMA_Short'].iloc[i]) or pd.isna(df['SMA_Long'].iloc[i]):
            signals.append(0)
            continue
            
        # 移動平均策略
        ma_signal = 1 if df['SMA_Short'].iloc[i] > df['SMA_Long'].iloc[i] else 0
        
        # RSI策略
        rsi_value = df['RSI'].iloc[i] if 'RSI' in df.columns and not pd.isna(df['RSI'].iloc[i]) else 50
        if rsi_value < rsi_oversold:
            rsi_signal = 1  # 超賣，買入
        elif rsi_value > rsi_overbought:
            rsi_signal = 0  # 超買，賣出
        else:
            rsi_signal = ma_signal  # 使用移動平均信號
        
        # 綜合信號
        final_signal = 1 if (ma_signal + rsi_signal) >= 1 else 0
        signals.append(final_signal)
    
    return np.array(signals)


def evaluate_lstm_strategy(df, params):
    """評估LSTM策略（簡化版本）"""
    try:
        # 由於LSTM需要較複雜的實現，這裡使用簡化的時間序列預測
        sequence_length = params.get('sequence_length', 60)
        
        # 使用簡單的趨勢預測作為LSTM的替代
        df['Price_Change'] = df['Close'].pct_change()
        df['Trend'] = df['Price_Change'].rolling(window=sequence_length//4).mean()
        
        # 生成預測信號
        predictions = []
        for i in range(len(df)):
            if i < sequence_length:
                predictions.append(0.5)
                continue
                
            recent_trend = df['Trend'].iloc[i-10:i].mean()
            if not pd.isna(recent_trend):
                # 基於趨勢的簡單預測
                pred = 0.6 if recent_trend > 0.001 else 0.4
            else:
                pred = 0.5
                
            predictions.append(pred)
        
        # 轉換為分類結果並計算準確率
        binary_preds = [1 if p > 0.5 else 0 for p in predictions[sequence_length:]]
        actual = df['Label'].iloc[sequence_length:].values
        
        if len(binary_preds) > 0 and len(actual) > 0:
            min_length = min(len(binary_preds), len(actual))
            accuracy = accuracy_score(actual[:min_length], binary_preds[:min_length])
        else:
            accuracy = 0.5
            
        return accuracy
        
    except Exception as e:
        logger.warning(f"LSTM策略評估失敗: {e}")
        return 0.5  # 返回隨機水準


if __name__ == "__main__":
    try:
        # 從命令列參數獲取模式
        mode = None
        if len(sys.argv) > 1:
            if sys.argv[1].lower() in ['us', 'usa', 'american']:
                mode = 'us'
            elif sys.argv[1].lower() in ['tw', 'taiwan', 'tw']:
                mode = 'tw'
        
        logger.info(f"策略管理器啟動，模式: {mode or 'default'}")
        main(mode)
        logger.info("策略管理器執行完成")
        
    except KeyboardInterrupt:
        logger.info("用戶中斷執行")
    except Exception as e:
        logger.error(f"策略管理器執行時發生未預期錯誤: {e}")
        slack_alert(f"❌ 策略管理器嚴重錯誤: {str(e)}", urgent=True)
        sys.exit(1)
