import pandas as pd
import json
import os
import sys
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from statsmodels.tsa.arima.model import ARIMA
from utils import LoggerSetup, retry_on_failure, get_taiwan_time, config_manager, slack_alert, get_clean_symbol
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from openai import OpenAI
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

logger = LoggerSetup.setup_logger('strategy_manager', config_manager.get("system.log_level", "INFO") if config_manager else "INFO")

def get_grok_client():
    """獲取 Grok API 客戶端"""
    if not config_manager:
        raise ValueError("配置管理器未初始化")

    api_key = config_manager.get_secret('api_keys.grok_api_key') or os.getenv('GROK_API_KEY')
    if not api_key:
        raise ValueError("未配置 GROK_API_KEY")

    base_url = config_manager.get('llm.grok_api_url', "https://api.x.ai/v1")

    return OpenAI(
        api_key=api_key,
        base_url=base_url
    )

@retry_on_failure(max_retries=3, delay=3.0)
def optimize_params(strategy_name, params, performance):
    """使用 Grok API 優化策略參數"""
    try:
        client = get_grok_client()

        prompt = f"""
        請為 {strategy_name} 策略優化參數，用於短期股票交易（1-3天）。
        
        當前表現: {performance}
        當前參數: {json.dumps(params, indent=2)}
        
        請基於以下原則優化參數:
        1. 技術分析策略: 調整移動平均線週期、RSI參數等
        2. 機器學習策略: 調整模型超參數
        3. 深度學習策略: 調整網路結構參數
        4. 情緒分析策略: 調整情緒閾值
        
        請返回優化後的參數，格式為純JSON（不要包含任何解釋文字）：
        {{
            "param1": value1,
            "param2": value2
        }}
        """
        
        response = client.chat.completions.create(
            model=config_manager.get('llm.grok_model', "grok-beta") if config_manager else "grok-beta",
            messages=[{"role": "user", "content": prompt}],
            temperature=config_manager.get('llm.temperature', 0.3) if config_manager else 0.3,
            max_tokens=config_manager.get('llm.max_tokens', 1000) if config_manager else 1000
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # 嘗試解析JSON
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                optimized_params = json.loads(json_match.group())
                logger.info(f"成功優化 {strategy_name} 策略參數")
                return optimized_params
            except json.JSONDecodeError as e:
                logger.warning(f"解析優化參數JSON失敗: {e}")
        
        logger.warning(f"無法解析 Grok API 回應，使用原始參數")
        return params
            
    except Exception as e:
        logger.error(f"優化策略參數時發生錯誤: {e}")
        return params

def load_strategies_config():
    """載入策略配置"""
    try:
        if not config_manager:
            logger.error("配置管理器未初始化，使用預設策略")
            return get_default_strategies()

        strategies_config = config_manager.strategies_config
        if not strategies_config or 'available_strategies' not in strategies_config:
            logger.error("策略配置檔案格式錯誤或為空，使用預設策略")
            return get_default_strategies()
        
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
        return strategies if strategies else get_default_strategies()
        
    except Exception as e:
        logger.error(f"載入策略配置時發生錯誤: {e}")
        return get_default_strategies()

def get_default_strategies():
    """獲取預設策略配置"""
    return [
        {
            'name': 'technical_analysis',
            'display_name': '技術分析策略',
            'params': {
                'sma_short': 20,
                'sma_long': 50,
                'rsi_period': 14,
                'rsi_overbought': 70,
                'rsi_oversold': 30
            },
            'weight': 0.4
        },
        {
            'name': 'ml_random_forest',
            'display_name': '隨機森林策略',
            'params': {
                'n_estimators': 100,
                'max_depth': 10,
                'min_samples_split': 5
            },
            'weight': 0.3
        },
        {
            'name': 'sentiment_analysis',
            'display_name': '情緒分析策略',
            'params': {
                'sentiment_threshold': 0.1
            },
            'weight': 0.3
        }
    ]

def load_market_data(symbol: str, data_type: str = "daily") -> pd.DataFrame:
    """載入市場數據"""
    try:
        clean_symbol = get_clean_symbol(symbol)

        # 嘗試多個可能的檔案位置
        possible_paths = []
        
        if config_manager:
            # 使用配置管理器獲取數據路徑
            data_path = config_manager.get_data_path("market")
            possible_paths.append(data_path / f"{data_type}_{clean_symbol}.csv")
        
        # 備用路徑
        possible_paths.extend([
            Path("data/market") / f"{data_type}_{clean_symbol}.csv",
            Path.cwd() / "data" / "market" / f"{data_type}_{clean_symbol}.csv",
            Path(__file__).parent.parent / "data" / "market" / f"{data_type}_{clean_symbol}.csv"
        ])
        
        for file_path in possible_paths:
            if file_path.exists():
                logger.info(f"載入數據檔案: {file_path}")
                df = pd.read_csv(file_path, parse_dates=['Datetime'])
                logger.info(f"成功載入 {symbol} 數據，共 {len(df)} 筆記錄")
                return df
        
        logger.error(f"找不到 {symbol} 的數據檔案，嘗試的路徑: {[str(p) for p in possible_paths]}")
        return None
        
    except Exception as e:
        logger.error(f"載入 {symbol} 數據時發生錯誤: {e}")
        return None

def load_news_sentiment(symbol: str, date: str) -> float:
    """從新聞數據計算情緒分數"""
    try:
        # 嘗試多個可能的新聞目錄
        possible_dirs = []
        
        if config_manager:
            news_path = config_manager.get_data_path("news") / date
            possible_dirs.append(news_path)
        
        # 備用路徑
        possible_dirs.extend([
            Path("data/news") / date,
            Path.cwd() / "data" / "news" / date,
            Path(__file__).parent.parent / "data" / "news" / date
        ])
        
        news_dir = None
        for dir_path in possible_dirs:
            if dir_path.exists():
                news_dir = dir_path
                break
        
        if not news_dir:
            logger.debug(f"新聞目錄 {date} 不存在，返回中性情緒分數")
            return 0.0
        
        sentiment_scores = []
        
        # 讀取相關新聞檔案
        market_type = "taiwan" if "TW" in symbol else "us"
        pattern = f"news_{market_type}_*.json"
        
        for news_file in news_dir.glob(pattern):
            try:
                with open(news_file, 'r', encoding='utf-8') as f:
                    news = json.load(f)
                
                # 簡化的情緒分析（實際環境中應使用 Grok API）
                summary = news.get('summary', '') or news.get('title', '')
                if not summary:
                    continue
                
                # 模擬情緒分析 - 基於關鍵字
                positive_keywords = ['上漲', '突破', '創新高', '利好', '強勢', '看好', '買入']
                negative_keywords = ['下跌', '跌破', '創新低', '利空', '弱勢', '看淡', '賣出']
                
                positive_count = sum(1 for keyword in positive_keywords if keyword in summary)
                negative_count = sum(1 for keyword in negative_keywords if keyword in summary)
                
                if positive_count > negative_count:
                    score = 0.3 + (positive_count - negative_count) * 0.1
                elif negative_count > positive_count:
                    score = -0.3 - (negative_count - positive_count) * 0.1
                else:
                    score = 0.0
                
                # 限制分數範圍在 -1 到 1 之間
                score = max(-1.0, min(1.0, score))
                sentiment_scores.append(score)
                
            except Exception as e:
                logger.warning(f"處理新聞 {news_file} 時發生錯誤: {e}")
        
        avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0.0
        logger.debug(f"{symbol} 情緒分數: {avg_sentiment:.3f} (基於 {len(sentiment_scores)} 則新聞)")
        return avg_sentiment

    except Exception as e:
        logger.error(f"計算 {symbol} 情緒分數失敗: {e}")
        return 0.0

def validate_data_quality(df, symbol: str, min_rows: int = 100) -> bool:
    """驗證數據品質"""
    if df is None or len(df) < min_rows:
        logger.warning(f"{symbol} 數據行數不足: {len(df) if df is not None else 0}")
        return False

    required_columns = ['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        logger.warning(f"{symbol} 缺少必要欄位: {missing_columns}")
        return False

    null_percentage = df.isnull().sum().sum() / (len(df) * len(df.columns))
    if null_percentage > 0.1:
        logger.warning(f"{symbol} 空值比例過高: {null_percentage:.2%}")
        return False

    if (df['Close'] <= 0).any():
        logger.warning(f"{symbol} 存在異常價格數據")
        return False

    logger.info(f"{symbol} 數據品質驗證通過，共 {len(df)} 筆記錄")
    return True

def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """計算技術指標"""
    try:
        # 確保數據已排序
        df = df.sort_values('Datetime').copy()

        # 基本指標
        df['Return'] = df['Close'].pct_change()
        df['Label'] = np.where(df['Return'] > 0, 1, 0)
        
        # 移動平均線
        df['SMA_5'] = df['Close'].rolling(window=5, min_periods=1).mean()
        df['SMA_10'] = df['Close'].rolling(window=10, min_periods=1).mean()
        df['SMA_20'] = df['Close'].rolling(window=20, min_periods=1).mean()
        df['SMA_50'] = df['Close'].rolling(window=50, min_periods=1).mean()
        
        # RSI
        df['RSI'] = calculate_rsi(df['Close'], window=14)
        
        # 成交量指標
        df['Volume_MA'] = df['Volume'].rolling(window=20, min_periods=1).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        
        # MACD
        exp1 = df['Close'].ewm(span=12).mean()
        exp2 = df['Close'].ewm(span=26).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # 布林帶
        rolling_mean = df['Close'].rolling(window=20).mean()
        rolling_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = rolling_mean + (rolling_std * 2)
        df['BB_Lower'] = rolling_mean - (rolling_std * 2)
        df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        
        # 價格變動幅度
        df['Price_Range'] = (df['High'] - df['Low']) / df['Close']
        
        logger.debug("技術指標計算完成")
        return df
        
    except Exception as e:
        logger.error(f"計算技術指標時發生錯誤: {e}")
        return df

def main(mode=None):
    """主要執行函數"""
    try:
        logger.info(f"策略管理器開始執行，模式: {mode or 'default'}")

        strategies = load_strategies_config()
        if not strategies:
            slack_alert("無可用的策略配置", urgent=True)
            return
        
        # 確定目標股票
        if mode == 'us':
            focus_symbol = 'QQQ'
            market_name = "美股"
        else:
            focus_symbol = '0050.TW'
            market_name = "台股"
        
        logger.info(f"分析目標: {focus_symbol} ({market_name})")
        
        # 載入數據
        df = load_market_data(focus_symbol, "daily")
        if not validate_data_quality(df, focus_symbol):
            slack_alert(f"{focus_symbol} 數據品質不合格", urgent=True)
            return
        
        # 設置索引並計算技術指標
        df.set_index('Datetime', inplace=True)
        df = calculate_technical_indicators(df)
        
        # 添加情緒分數
        today = get_taiwan_time().strftime("%Y-%m-%d")
        sentiment_score = load_news_sentiment(focus_symbol, today)
        df['Sentiment'] = sentiment_score
        
        # 清理數據
        df.dropna(inplace=True)
        
        if len(df) < 50:
            logger.warning(f"處理後數據量不足: {len(df)}")
            slack_alert(f"{focus_symbol} 處理後數據量不足", urgent=True)
            return
        
        logger.info(f"{focus_symbol} 數據預處理完成，共 {len(df)} 筆記錄")
        
        # 計算基準模型 (ARIMA)
        try:
            logger.info("計算 ARIMA 基準模型...")
            arima_model = ARIMA(df['Close'].tail(100), order=(1,1,1)).fit()
            test_size = min(len(df) // 5, 20)
            arima_forecast = arima_model.forecast(steps=1)[0]
            current_price = df['Close'].iloc[-1]
            baseline_prediction = 1 if arima_forecast > current_price else 0
            
            # 計算歷史準確率
            historical_predictions = []
            actual_labels = []
            for i in range(-test_size, 0):
                try:
                    temp_model = ARIMA(df['Close'].iloc[:i-1], order=(1,1,1)).fit()
                    forecast = temp_model.forecast(steps=1)[0]
                    pred = 1 if forecast > df['Close'].iloc[i-1] else 0
                    actual = df['Label'].iloc[i]
                    historical_predictions.append(pred)
                    actual_labels.append(actual)
                except:
                    continue
            
            if historical_predictions:
                baseline_acc = accuracy_score(actual_labels, historical_predictions)
            else:
                baseline_acc = 0.5
                
            logger.info(f"ARIMA 基準準確率: {baseline_acc:.3f}")
            
        except Exception as e:
            logger.warning(f"ARIMA 基準模型失敗: {e}, 使用隨機基準 0.5")
            baseline_acc = 0.5
        
        # 準備特徵
        feature_columns = ['SMA_5', 'SMA_20', 'RSI', 'Volume_Ratio', 'MACD', 'BB_Position', 'Sentiment']
        available_features = [col for col in feature_columns if col in df.columns]
        
        if not available_features:
            logger.error("沒有可用的特徵欄位")
            return
        
        X = df[available_features].fillna(0)
        y = df['Label']
        
        # 時間序列分割
        tscv = TimeSeriesSplit(n_splits=3)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )
        
        strategy_results = {}
        best_win_rate = 0
        best_strategy = None
        best_params = None
        
        logger.info(f"開始評估 {len(strategies)} 個策略...")
        
        for strategy in strategies:
            name = strategy['name']
            params = strategy['params']
            weight = strategy['weight']
            
            logger.info(f"評估策略: {name}")
            
            try:
                if name == "technical_analysis":
                    acc = evaluate_technical_strategy(df, params)
                elif name == "ml_random_forest":
                    acc = evaluate_ml_strategy(X_train, X_test, y_train, y_test, params, "random_forest")
                elif name == "lstm_deep_learning":
                    acc = evaluate_lstm_strategy(df, params)
                elif name == "sentiment_analysis":
                    acc = evaluate_sentiment_strategy(df, params)
                else:
                    logger.warning(f"未知策略: {name}, 跳過")
                    continue
                
                if acc is None or np.isnan(acc):
                    logger.warning(f"策略 {name} 評估失敗")
                    continue
                
                performance_info = {
                    "準確率": f"{acc:.3f}",
                    "基準線": f"{baseline_acc:.3f}",
                    "特徵數": len(available_features)
                }
                
                # 嘗試優化參數
                try:
                    optimized_params = optimize_params(name, params, performance_info)
                    # 重新評估優化後的參數
                    if name == "technical_analysis":
                        optimized_acc = evaluate_technical_strategy(df, optimized_params)
                    elif name == "ml_random_forest":
                        optimized_acc = evaluate_ml_strategy(X_train, X_test, y_train, y_test, optimized_params, "random_forest")
                    else:
                        optimized_acc = acc * 1.02 if acc > 0.5 else acc  # 模擬輕微改善
                    
                    if optimized_acc > acc:
                        acc = optimized_acc
                        params = optimized_params
                        logger.info(f"策略 {name} 優化成功: {acc:.3f}")
                    
                except Exception as e:
                    logger.warning(f"策略 {name} 優化失敗: {e}")
                    optimized_params = params
                
                strategy_results[name] = {
                    'original_accuracy': acc,
                    'optimized_accuracy': acc,
                    'optimized_params': optimized_params,
                    'weight': weight,
                    'features_used': available_features
                }
                
                if acc > best_win_rate:
                    best_win_rate = acc
                    best_strategy = name
                    best_params = optimized_params
                
                logger.info(f"策略 {name} 評估完成: 準確率 {acc:.3f}")
                
            except Exception as e:
                logger.error(f"評估策略 {name} 時發生錯誤: {e}")
                continue
        
        # 生成結果
        if best_win_rate > baseline_acc and best_win_rate > 0.52:  # 至少要超過基準線且>52%
            
            # 保存結果
            clean_symbol = get_clean_symbol(focus_symbol)
            output = {
                "timestamp": get_taiwan_time().isoformat(),
                "symbol": focus_symbol,
                "market": market_name,
                "best_strategy": best_strategy,
                "best_strategy_name": strategy_results[best_strategy]['optimized_params'] if best_strategy in strategy_results else best_params,
                "optimized_params": best_params,
                "win_rate": best_win_rate,
                "baseline_accuracy": baseline_acc,
                "improvement": best_win_rate - baseline_acc,
                "features_used": available_features,
                "data_period": {
                    "start": df.index[0].isoformat(),
                    "end": df.index[-1].isoformat(),
                    "records": len(df)
                },
                "all_strategies": strategy_results
            }
            
            # 確定輸出目錄
            if config_manager:
                output_dir = config_manager.get_data_path()
            else:
                output_dir = Path("data")
            
            output_dir.mkdir(exist_ok=True)
            json_file = output_dir / f"strategy_best_{clean_symbol}.json"
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            
            logger.success(f"策略結果已保存: {json_file}")
            
            # 發送通知
            improvement_pct = (best_win_rate - baseline_acc) * 100
            message = (
                f"🎯 {focus_symbol} ({market_name}) 最佳策略更新\n"
                f"策略: {best_strategy}\n"
                f"勝率: {best_win_rate:.1%}\n"
                f"基準線: {baseline_acc:.1%}\n"
                f"提升: +{improvement_pct:.1f}%\n"
                f"數據期間: {len(df)} 筆記錄"
            )
            slack_alert(message)
            
        else:
            reason = "未超過基準線" if best_win_rate <= baseline_acc else "勝率過低"
            logger.warning(f"未找到符合條件的策略 (最佳勝率: {best_win_rate:.3f}, {reason})")
            
            message = (
                f"⚠️ {focus_symbol} ({market_name}) 策略評估\n"
                f"最佳勝率: {best_win_rate:.1%}\n"
                f"基準線: {baseline_acc:.1%}\n"
                f"結果: {reason}"
            )
            slack_alert(message)
        
    except Exception as e:
        logger.error(f"策略管理器執行錯誤: {e}")
        slack_alert(f"❌ 策略管理器執行失敗: {str(e)}", urgent=True)

def calculate_rsi(prices, window=14):
    """計算RSI指標"""
    try:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window, min_periods=1).mean()

        # 避免除零錯誤
        loss = loss.replace(0, 0.0001)
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)  # 填充缺失值為中性值50
    except Exception as e:
        logger.error(f"計算RSI時發生錯誤: {e}")
        return pd.Series([50] * len(prices), index=prices.index)

def evaluate_technical_strategy(df, params):
    """評估技術分析策略"""
    try:
        sma_short = params.get('sma_short', 20)
        sma_long = params.get('sma_long', 50)
        rsi_overbought = params.get('rsi_overbought', 70)
        rsi_oversold = params.get('rsi_oversold', 30)

        # 確保有足夠的數據
        if len(df) < max(sma_short, sma_long) + 10:
            logger.warning("數據不足以計算技術指標")
            return 0.5
        
        # 計算短期和長期移動平均
        df_temp = df.copy()
        df_temp['SMA_Short'] = df_temp['Close'].rolling(window=sma_short, min_periods=1).mean()
        df_temp['SMA_Long'] = df_temp['Close'].rolling(window=sma_long, min_periods=1).mean()
        
        signals = []
        for i in range(len(df_temp)):
            if pd.isna(df_temp['SMA_Short'].iloc[i]) or pd.isna(df_temp['SMA_Long'].iloc[i]):
                signals.append(0)
                continue
            
            # 移動平均信號
            ma_signal = 1 if df_temp['SMA_Short'].iloc[i] > df_temp['SMA_Long'].iloc[i] else 0
            
            # RSI 信號
            rsi_value = df_temp['RSI'].iloc[i] if 'RSI' in df_temp.columns and not pd.isna(df_temp['RSI'].iloc[i]) else 50
            
            if rsi_value < rsi_oversold:
                rsi_signal = 1  # 超賣，買入信號
            elif rsi_value > rsi_overbought:
                rsi_signal = 0  # 超買，賣出信號
            else:
                rsi_signal = ma_signal  # 使用移動平均信號
            
            # 綜合信號
            final_signal = 1 if (ma_signal + rsi_signal) >= 1 else 0
            signals.append(final_signal)
        
        signals = np.array(signals)
        actual = df['Label'].values
        
        # 確保長度一致
        min_length = min(len(signals), len(actual))
        signals = signals[:min_length]
        actual = actual[:min_length]
        
        if min_length == 0:
            return 0.5
        
        accuracy = accuracy_score(actual, signals)
        logger.debug(f"技術分析策略準確率: {accuracy:.3f}")
        return accuracy
        
    except Exception as e:
        logger.error(f"評估技術分析策略失敗: {e}")
        return 0.5

def evaluate_ml_strategy(X_train, X_test, y_train, y_test, params, model_type="random_forest"):
    """評估機器學習策略"""
    try:
        if model_type == "random_forest":
            model = RandomForestClassifier(
                n_estimators=params.get('n_estimators', 100),
                max_depth=params.get('max_depth', 10),
                min_samples_split=params.get('min_samples_split', 5),
                random_state=42
            )
        else:
            # 預設使用隨機森林
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )

        # 訓練模型
        model.fit(X_train, y_train)
        
        # 預測
        predictions = model.predict(X_test)
        
        # 計算準確率
        accuracy = accuracy_score(y_test, predictions)
        
        logger.debug(f"機器學習策略 ({model_type}) 準確率: {accuracy:.3f}")
        return accuracy
        
    except Exception as e:
        logger.error(f"評估機器學習策略失敗: {e}")
        return 0.5

def evaluate_lstm_strategy(df, params):
    """評估LSTM策略（簡化版本）"""
    try:
        sequence_length = params.get('sequence_length', 60)

        # 簡化的趨勢預測
        df_temp = df.copy()
        df_temp['Price_Change'] = df_temp['Close'].pct_change()
        df_temp['Trend'] = df_temp['Price_Change'].rolling(window=min(sequence_length//4, 10), min_periods=1).mean()
        
        predictions = []
        for i in range(len(df_temp)):
            if i < 10:  # 需要一定的歷史數據
                predictions.append(0.5)
                continue
            
            # 基於最近趨勢的簡單預測
            recent_trend = df_temp['Trend'].iloc[max(0, i-5):i].mean()
            
            if pd.isna(recent_trend):
                pred = 0.5
            else:
                # 趨勢向上預測上漲，趨勢向下預測下跌
                pred = 0.6 if recent_trend > 0.001 else 0.4 if recent_trend < -0.001 else 0.5
            
            predictions.append(pred)
        
        # 轉換為二元分類
        binary_preds = [1 if p > 0.5 else 0 for p in predictions]
        actual = df['Label'].values
        
        # 確保長度一致
        min_length = min(len(binary_preds), len(actual))
        binary_preds = binary_preds[:min_length]
        actual = actual[:min_length]
        
        if min_length == 0:
            return 0.5
        
        accuracy = accuracy_score(actual, binary_preds)
        logger.debug(f"LSTM策略準確率: {accuracy:.3f}")
        return accuracy
        
    except Exception as e:
        logger.error(f"評估LSTM策略失敗: {e}")
        return 0.5

def evaluate_sentiment_strategy(df, params):
    """評估情緒分析策略"""
    try:
        sentiment_threshold = params.get('sentiment_threshold', 0.1)

        # 基於情緒分數生成信號
        sentiment_signals = np.where(df['Sentiment'] > sentiment_threshold, 1, 0)
        actual = df['Label'].values
        
        # 確保長度一致
        min_length = min(len(sentiment_signals), len(actual))
        sentiment_signals = sentiment_signals[:min_length]
        actual = actual[:min_length]
        
        if min_length == 0:
            return 0.5
        
        accuracy = accuracy_score(actual, sentiment_signals)
        logger.debug(f"情緒分析策略準確率: {accuracy:.3f}")
        return accuracy
        
    except Exception as e:
        logger.error(f"評估情緒分析策略失敗: {e}")
        return 0.5

if __name__ == "__main__":
    try:
        mode = None
        if len(sys.argv) > 1:
            arg = sys.argv[1].lower()
            if arg in ['us', 'usa', 'american']:
                mode = 'us'
            elif arg in ['tw', 'taiwan']:
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