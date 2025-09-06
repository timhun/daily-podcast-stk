# strategy_mastermind.py
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing as mp
from copy import deepcopy
import itertools

# Third-party imports with error handling
try:
    from xai_sdk import Client
    from xai_sdk.chat import user, system
    XAI_AVAILABLE = True
except ImportError:
    print("Warning: xai_sdk not available. AI optimization will be disabled.")
    XAI_AVAILABLE = False

try:
    from loguru import logger
    import ta
    import matplotlib.pyplot as plt
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Missing dependencies: {e}")
    DEPENDENCIES_AVAILABLE = False

@dataclass
class BacktestResult:
    """Standardized backtest result structure"""
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    expected_return: float = 0.0
    signals: Dict[str, Any] = None
    additional_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.signals is None:
            self.signals = {
                'position': 'NEUTRAL',
                'entry_price': 0.0,
                'target_price': 0.0,
                'stop_loss': 0.0,
                'position_size': 0.0
            }
        if self.additional_metrics is None:
            self.additional_metrics = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'expected_return': self.expected_return,
            'signals': self.signals,
            **self.additional_metrics
        }

class ConfigManager:
    """Centralized configuration management"""
    
    def __init__(self, config_path: str = 'config.json'):
        self.config_path = config_path
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration with error handling"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file {self.config_path} not found")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Fallback configuration"""
        return {
            'data_paths': {
                'market': 'data/market',
                'charts': 'data/charts',
                'strategy': 'data/strategy'
            },
            'technical_params': {
                'rsi_window': 14,
                'sma_window': 20,
                'rsi_buy_threshold': 30,
                'rsi_sell_threshold': 70,
                'min_data_length': 50
            },
            'strategy_params': {
                'daily_multiplier': 1.05,
                'hourly_multiplier': 1.02,
                'stop_loss_ratio': 0.95,
                'position_size': 0.5,
                'sharpe_annualization_daily': 252,
                'sharpe_annualization_hourly': 2520,
                'max_drawdown_threshold': 0.15
            },
            'symbols': {'tw': [], 'us': []},
            'logging': {'file': 'logs/strategy.log', 'rotation': '1 MB'}
        }
    
    def _validate_config(self):
        """Validate critical configuration keys"""
        required_keys = ['data_paths', 'strategy_params', 'symbols']
        for key in required_keys:
            if key not in self.config:
                logger.warning(f"Missing config key: {key}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Safe config access"""
        return self.config.get(key, default)

class DataCache:
    """Thread-safe data caching"""
    
    def __init__(self):
        self._cache = {}
        self._lock = mp.Lock()
    
    def get_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Get cached data or load from file"""
        key = f"{symbol}_{timeframe}"
        
        with self._lock:
            if key in self._cache:
                return self._cache[key].copy()
        
        # Load data if not cached
        data = self._load_data(symbol, timeframe)
        if data is not None:
            with self._lock:
                self._cache[key] = data
            return data.copy()
        
        return None
    
    def _load_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Load data from CSV file"""
        file_path = self._build_file_path(symbol, timeframe)
        if not os.path.exists(file_path):
            logger.error(f"Data file not found: {file_path}")
            return None
        
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                logger.error(f"Empty data file: {file_path}")
                return None
            return df
        except Exception as e:
            logger.error(f"Failed to load data from {file_path}: {e}")
            return None
    
    @staticmethod
    def _build_file_path(symbol: str, timeframe: str) -> str:
        """Build file path for symbol data"""
        config = ConfigManager().config
        market_dir = config['data_paths']['market']
        safe_symbol = symbol.replace('^', '').replace('.', '_').replace('/', '_')
        return f"{market_dir}/{timeframe}_{safe_symbol}.csv"
    
    def clear_cache(self):
        """Clear all cached data"""
        with self._lock:
            self._cache.clear()

class StrategyBase:
    """Base class for all strategies"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.data_cache = DataCache()
        self.params = self._get_default_params()
        
    def _get_default_params(self) -> Dict[str, Any]:
        """Override in subclasses"""
        return {}
    
    def backtest(self, symbol: str, data: Dict[str, Any], timeframe: str = 'daily') -> BacktestResult:
        """Main backtest method - override in subclasses"""
        raise NotImplementedError("Subclasses must implement backtest method")
    
    def _calculate_metrics(self, df: pd.DataFrame, timeframe: str) -> Tuple[float, float, float]:
        """Calculate standard performance metrics"""
        if 'strategy_returns' not in df.columns or df['strategy_returns'].std() == 0:
            return 0.0, 0.0, 0.0
        
        # Sharpe ratio
        annualization = (self.config.get('strategy_params', {})
                        .get('sharpe_annualization_daily' if timeframe == 'daily' else 'sharpe_annualization_hourly', 252))
        sharpe_ratio = (df['strategy_returns'].mean() / df['strategy_returns'].std() * 
                       np.sqrt(annualization))
        
        # Maximum drawdown
        cum_returns = df['strategy_returns'].cumsum()
        max_drawdown = (cum_returns.cummax() - cum_returns).max()
        
        # Expected return
        expected_return = (df['strategy_returns'].mean() * 
                         (self.config.get('strategy_params', {})
                          .get('expected_return_annualization_daily' if timeframe == 'daily' else 'expected_return_annualization_hourly', 252)))
        
        # Handle NaN values
        sharpe_ratio = sharpe_ratio if not np.isnan(sharpe_ratio) else 0.0
        max_drawdown = max_drawdown if not np.isnan(max_drawdown) else 0.0
        expected_return = expected_return if not np.isnan(expected_return) else 0.0
        
        return sharpe_ratio, max_drawdown, expected_return
    
    def _generate_signals(self, df: pd.DataFrame, timeframe: str) -> Dict[str, Any]:
        """Generate trading signals based on latest data"""
        if df.empty:
            return {
                'position': 'NEUTRAL',
                'entry_price': 0.0,
                'target_price': 0.0,
                'stop_loss': 0.0,
                'position_size': 0.0
            }
        
        latest_close = df['close'].iloc[-1]
        latest_signal = df.get('signal', pd.Series([0])).iloc[-1]
        
        multiplier_key = 'daily_multiplier' if timeframe == 'daily' else 'hourly_multiplier'
        multiplier = self.config.get('strategy_params', {}).get(multiplier_key, 1.05)
        stop_loss_ratio = self.config.get('strategy_params', {}).get('stop_loss_ratio', 0.95)
        position_size = self.config.get('strategy_params', {}).get('position_size', 0.5)
        
        position_map = {1: 'LONG', -1: 'SHORT', 0: 'NEUTRAL'}
        
        return {
            'position': position_map.get(latest_signal, 'NEUTRAL'),
            'entry_price': latest_close,
            'target_price': latest_close * multiplier,
            'stop_loss': latest_close * stop_loss_ratio,
            'position_size': position_size
        }

class TechnicalAnalysis(StrategyBase):
    """RSI and SMA based technical analysis strategy"""
    
    def _get_default_params(self) -> Dict[str, Any]:
        return self.config.get('technical_params', {
            'rsi_window': 14,
            'rsi_buy_threshold': 30,
            'rsi_sell_threshold': 70,
            'sma_window': 20,
            'min_data_length': 50
        })
    
    def backtest(self, symbol: str, data: Dict[str, Any], timeframe: str = 'daily') -> BacktestResult:
        """Technical analysis backtest"""
        if not DEPENDENCIES_AVAILABLE:
            logger.error("Dependencies not available for technical analysis")
            return BacktestResult()
        
        df = self.data_cache.get_data(symbol, timeframe)
        if df is None or len(df) < self.params.get('min_data_length', 50):
            logger.error(f"{symbol} insufficient data for technical analysis")
            return BacktestResult()
        
        try:
            # Calculate technical indicators
            df['rsi'] = ta.momentum.RSIIndicator(
                df['close'], 
                window=self.params.get('rsi_window', 14)
            ).rsi()
            
            df['sma'] = ta.trend.SMAIndicator(
                df['close'], 
                window=self.params.get('sma_window', 20)
            ).sma_indicator()
            
            # Generate signals
            df['signal'] = 0
            buy_threshold = self.params.get('rsi_buy_threshold', 30)
            sell_threshold = self.params.get('rsi_sell_threshold', 70)
            
            df.loc[df['rsi'] < buy_threshold, 'signal'] = 1
            df.loc[df['rsi'] > sell_threshold, 'signal'] = -1
            
            # Calculate returns
            df['returns'] = df['close'].pct_change()
            df['strategy_returns'] = df['returns'] * df['signal'].shift(1)
            
            # Calculate metrics
            sharpe_ratio, max_drawdown, expected_return = self._calculate_metrics(df, timeframe)
            signals = self._generate_signals(df, timeframe)
            
            return BacktestResult(
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                expected_return=expected_return,
                signals=signals,
                additional_metrics={'strategy_type': 'technical'}
            )
            
        except Exception as e:
            logger.error(f"Technical analysis backtest failed for {symbol}: {e}")
            return BacktestResult()

class QuantityStrategy(StrategyBase):
    """Volume-price based strategy"""
    
    def _get_default_params(self) -> Dict[str, Any]:
        quantity_params = self.config.get('strategy_params', {}).get('quantity_params', {})
        return {
            'volume_ma_period': quantity_params.get('volume_ma_period', 5),
            'volume_multiplier': quantity_params.get('volume_multiplier', 1.2),
            'stop_profit': quantity_params.get('stop_profit', 0.02),
            'stop_loss': quantity_params.get('stop_loss', 0.02),
            'risk_per_trade': quantity_params.get('risk_per_trade', 0.02)
        }
    
    def backtest(self, symbol: str, data: Dict[str, Any], timeframe: str = 'daily') -> BacktestResult:
        """Volume-price strategy backtest"""
        if not DEPENDENCIES_AVAILABLE:
            logger.error("Dependencies not available for quantity strategy")
            return BacktestResult()
        
        df = self.data_cache.get_data(symbol, timeframe)
        if df is None or len(df) < self.params.get('volume_ma_period', 5):
            logger.error(f"{symbol} insufficient data for quantity strategy")
            return BacktestResult()
        
        try:
            # Calculate volume indicators
            volume_window = self.params.get('volume_ma_period', 5)
            df['volume_ma'] = ta.trend.SMAIndicator(df['volume'], window=volume_window).sma_indicator()
            df['volume_rate'] = df['volume'] / df['volume_ma'].replace(0, np.nan)
            df['returns'] = df['close'].pct_change()
            
            # Generate signals with position tracking
            df['signal'] = 0
            position = 0
            entry_price = 0
            trades = []
            win_count = 0
            
            volume_multiplier = self.params.get('volume_multiplier', 1.2)
            stop_profit = self.params.get('stop_profit', 0.02)
            stop_loss = self.params.get('stop_loss', 0.02)
            
            for i in range(1, len(df)):
                current_volume_rate = df['volume_rate'].iloc[i]
                current_price = df['close'].iloc[i]
                prev_price = df['close'].iloc[i-1]
                
                # Entry condition
                if (current_volume_rate > volume_multiplier and 
                    current_price > prev_price and 
                    position == 0):
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                    position = 1
                    entry_price = current_price
                
                # Exit conditions
                elif position == 1:
                    exit_signal = False
                    trade_return = 0
                    
                    # Normal exit
                    if current_volume_rate < 1 and current_price < prev_price:
                        exit_signal = True
                        trade_return = (current_price - entry_price) / entry_price
                    
                    # Take profit
                    elif current_price >= entry_price * (1 + stop_profit):
                        exit_signal = True
                        trade_return = stop_profit
                    
                    # Stop loss
                    elif current_price <= entry_price * (1 - stop_loss):
                        exit_signal = True
                        trade_return = -stop_loss
                    
                    if exit_signal:
                        df.iloc[i, df.columns.get_loc('signal')] = -1
                        position = 0
                        trades.append(trade_return)
                        if trade_return > 0:
                            win_count += 1
            
            # Calculate strategy returns
            df['strategy_returns'] = df['returns'] * df['signal'].shift(1)
            
            # Calculate metrics
            sharpe_ratio, max_drawdown, expected_return = self._calculate_metrics(df, timeframe)
            signals = self._generate_signals(df, timeframe)
            signals['position_size'] = self.params.get('risk_per_trade', 0.02)
            
            # Additional metrics
            win_rate = win_count / len(trades) if trades else 0
            
            return BacktestResult(
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                expected_return=expected_return,
                signals=signals,
                additional_metrics={
                    'strategy_type': 'quantity',
                    'win_rate': win_rate,
                    'total_trades': len(trades)
                }
            )
            
        except Exception as e:
            logger.error(f"Quantity strategy backtest failed for {symbol}: {e}")
            return BacktestResult()

class RandomForestStrategy(StrategyBase):
    """Machine learning based strategy using Random Forest"""
    
    def _get_default_params(self) -> Dict[str, Any]:
        ml_params = self.config.get('ml_params', {})
        return {
            'rf_estimators': ml_params.get('rf_estimators', 100),
            'rf_random_state': ml_params.get('rf_random_state', 42),
            'ml_test_size': ml_params.get('ml_test_size', 0.2),
            'ml_features': ml_params.get('ml_features', ['open', 'high', 'low', 'close', 'volume']),
            'min_data_length': ml_params.get('min_data_length_ml', 100)
        }
    
    def backtest(self, symbol: str, data: Dict[str, Any], timeframe: str = 'daily') -> BacktestResult:
        """Random Forest strategy backtest"""
        if not DEPENDENCIES_AVAILABLE:
            logger.error("Dependencies not available for ML strategy")
            return BacktestResult()
        
        df = self.data_cache.get_data(symbol, timeframe)
        min_length = self.params.get('min_data_length', 100)
        
        if df is None or len(df) < min_length:
            logger.error(f"{symbol} insufficient data for ML strategy")
            return BacktestResult()
        
        try:
            # Feature engineering
            features = self.params.get('ml_features', ['open', 'high', 'low', 'close', 'volume'])
            
            # Add technical indicators as features
            technical_params = self.config.get('technical_params', {})
            rsi_window = technical_params.get('rsi_window', 14)
            sma_window = technical_params.get('sma_window', 20)
            
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=rsi_window).rsi()
            df['sma'] = ta.trend.SMAIndicator(df['close'], window=sma_window).sma_indicator()
            df['returns'] = df['close'].pct_change()
            
            # Create target variable (next period return > 0)
            df['target'] = np.where(df['returns'].shift(-1) > 0, 1, 0)
            
            # Prepare features and target
            feature_cols = features + ['rsi', 'sma']
            X = df[feature_cols].dropna()
            y = df['target'].loc[X.index]
            
            if len(X) < min_length:
                logger.error(f"{symbol} insufficient clean data for ML: {len(X)} samples")
                return BacktestResult()
            
            # Train-test split
            test_size = self.params.get('ml_test_size', 0.2)
            random_state = self.params.get('rf_random_state', 42)
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state, shuffle=False
            )
            
            # Train model
            model = RandomForestClassifier(
                n_estimators=self.params.get('rf_estimators', 100),
                random_state=random_state
            )
            model.fit(X_train, y_train)
            
            # Predictions
            predictions = model.predict(X_test)
            accuracy = accuracy_score(y_test, predictions)
            
            # Generate signals
            df['signal'] = 0
            test_start_idx = X_test.index[0]
            df.loc[X_test.index, 'signal'] = predictions
            
            # Calculate strategy returns
            df['strategy_returns'] = df['returns'] * df['signal'].shift(1)
            
            # Calculate metrics
            sharpe_ratio, max_drawdown, expected_return = self._calculate_metrics(df, timeframe)
            signals = self._generate_signals(df, timeframe)
            
            return BacktestResult(
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                expected_return=expected_return,
                signals=signals,
                additional_metrics={
                    'strategy_type': 'random_forest',
                    'accuracy': accuracy,
                    'train_samples': len(X_train),
                    'test_samples': len(X_test)
                }
            )
            
        except Exception as e:
            logger.error(f"Random Forest strategy backtest failed for {symbol}: {e}")
            return BacktestResult()

class BigLineStrategy(StrategyBase):
    """Weighted moving average strategy with market correlation"""
    
    def _get_default_params(self) -> Dict[str, Any]:
        bigline_params = self.config.get('strategy_params', {}).get('bigline_params', {})
        return {
            'weights': bigline_params.get('weights', [0.4, 0.35, 0.25]),
            'ma_short': bigline_params.get('ma_short', 5),
            'ma_mid': bigline_params.get('ma_mid', 20),
            'ma_long': bigline_params.get('ma_long', 60),
            'vol_window': bigline_params.get('vol_window', 60)
        }
    
    def backtest(self, symbol: str, data: Dict[str, Any], timeframe: str = 'daily') -> BacktestResult:
        """BigLine strategy backtest"""
        if not DEPENDENCIES_AVAILABLE:
            return BacktestResult()
        
        # Determine market index
        symbols_config = self.config.get('symbols', {'tw': [], 'us': []})
        index_symbol = '^TWII' if symbol in symbols_config.get('tw', []) else '^IXIC'
        
        # Load data
        df = self.data_cache.get_data(symbol, timeframe)
        index_df = self.data_cache.get_data(index_symbol, timeframe)
        
        ma_long = self.params.get('ma_long', 60)
        if (df is None or len(df) < ma_long or 
            index_df is None or len(index_df) < ma_long):
            logger.error(f"{symbol} or index {index_symbol} insufficient data")
            return BacktestResult()
        
        try:
            # Prepare data with dates as index
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date').sort_index()
            
            if 'date' in index_df.columns:
                index_df['date'] = pd.to_datetime(index_df['date'])
                index_df = index_df.set_index('date').sort_index()
            
            # Merge with index data
            df = df.join(index_df[['close', 'volume']], rsuffix='_index', how='inner')
            
            if df.empty:
                logger.error(f"No overlapping data between {symbol} and {index_symbol}")
                return BacktestResult()
            
            # Calculate moving averages
            ma_short = self.params.get('ma_short', 5)
            ma_mid = self.params.get('ma_mid', 20)
            weights = self.params.get('weights', [0.4, 0.35, 0.25])
            
            prices = df['close']
            volume = df['volume']
            index_prices = df['close_index']
            
            # Stock moving averages
            ma_s = prices.rolling(window=ma_short).mean()
            ma_m = prices.rolling(window=ma_mid).mean()
            ma_l = prices.rolling(window=ma_long).mean()
            
            # Check trend alignment
            bullish = (ma_s > ma_m) & (ma_m > ma_l)
            
            # Calculate weighted big line
            big_line = (weights[0] * ma_s + weights[1] * ma_m + weights[2] * ma_l)
            
            # Volume adjustment
            vol_window = self.params.get('vol_window', 60)
            max_vol = volume.rolling(window=vol_window).max()
            vol_factor = 1 + volume / (max_vol + 1e-9)
            big_line_weighted = big_line * vol_factor
            big_line_diff = big_line_weighted.diff()
            
            # Index trend
            index_ma_s = index_prices.rolling(window=ma_short).mean()
            index_ma_m = index_prices.rolling(window=ma_mid).mean()
            index_ma_l = index_prices.rolling(window=ma_long).mean()
            index_bullish = (index_ma_s > index_ma_m) & (index_ma_m > index_ma_l)
            
            # Generate signals
            df['signal'] = 0
            long_condition = (big_line_diff > 0) & bullish & index_bullish
            short_condition = (big_line_diff < 0) & ~index_bullish
            
            df.loc[long_condition, 'signal'] = 1
            df.loc[short_condition, 'signal'] = -1
            
            # Calculate returns
            df['returns'] = df['close'].pct_change()
            df['strategy_returns'] = df['returns'] * df['signal'].shift(1)
            
            # Calculate metrics
            sharpe_ratio, max_drawdown, expected_return = self._calculate_metrics(df, timeframe)
            signals = self._generate_signals(df, timeframe)
            
            return BacktestResult(
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                expected_return=expected_return,
                signals=signals,
                additional_metrics={
                    'strategy_type': 'bigline',
                    'index_symbol': index_symbol
                }
            )
            
        except Exception as e:
            logger.error(f"BigLine strategy backtest failed for {symbol}: {e}")
            return BacktestResult()

class MarketAnalyst:
    """Market analysis and technical indicators"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.data_cache = DataCache()
    
    def analyze_market(self, symbol: str, timeframe: str = 'daily') -> Dict[str, Any]:
        """Comprehensive market analysis"""
        if not DEPENDENCIES_AVAILABLE:
            return self._get_default_analysis()
        
        df = self.data_cache.get_data(symbol, timeframe)
        if df is None or len(df) < 50:
            logger.error(f"{symbol} insufficient data for market analysis")
            return self._get_default_analysis()
        
        try:
            # Calculate technical indicators
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            df['macd'] = ta.trend.MACD(df['close']).macd()
            df['bb_high'] = ta.volatility.BollingerBands(df['close']).bollinger_hband()
            df['bb_low'] = ta.volatility.BollingerBands(df['close']).bollinger_lband()
            df['sma_50'] = ta.trend.SMAIndicator(df['close'], window=50).sma_indicator()
            df['sma_200'] = ta.trend.SMAIndicator(df['close'], window=200).sma_indicator()
            
            # Determine trend
            latest_sma_50 = df['sma_50'].iloc[-1]
            latest_sma_200 = df['sma_200'].iloc[-1]
            
            if pd.isna(latest_sma_50) or pd.isna(latest_sma_200):
                trend = 'NEUTRAL'
            elif latest_sma_50 > latest_sma_200:
                trend = 'BULLISH'
            elif latest_sma_50 < latest_sma_200:
                trend = 'BEARISH'
            else:
                trend = 'NEUTRAL'
            
            # Calculate volatility
            volatility = df['close'].pct_change().rolling(20).std().iloc[-1] * 100
            volatility = volatility if not pd.isna(volatility) else 0.0
            
            # Gather indicators
            indicators = {
                'rsi': df['rsi'].iloc[-1] if not pd.isna(df['rsi'].iloc[-1]) else 50.0,
                'macd': df['macd'].iloc[-1] if not pd.isna(df['macd'].iloc[-1]) else 0.0,
                'bollinger': {
                    'high': df['bb_high'].iloc[-1] if not pd.isna(df['bb_high'].iloc[-1]) else 0.0,
                    'low': df['bb_low'].iloc[-1] if not pd.isna(df['bb_low'].iloc[-1]) else 0.0
                }
            }
            
            report = (f"{symbol} 市場分析：趨勢 {trend}，波動性 {volatility:.2f}%，"
                     f"RSI {indicators['rsi']:.2f}，MACD {indicators['macd']:.4f}")
            
            logger.info(f"{symbol} market analysis completed")
            
            return {
                'trend': trend,
                'volatility': volatility,
                'technical_indicators': indicators,
                'report': report
            }
            
        except Exception as e:
            logger.error(f"Market analysis failed for {symbol}: {e}")
            return self._get_default_analysis()
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """Default analysis when data unavailable"""
        return {
            'trend': 'NEUTRAL',
            'volatility': 0.0,
            'technical_indicators': {
                'rsi': 50.0,
                'macd': 0.0,
                'bollinger': {'high': 0.0, 'low': 0.0}
            },
            'report': '無數據可分析'
        }

class ParameterOptimizer:
    """Parallel parameter optimization"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.param_grids = {
            'technical': {
                'rsi_window': [10, 14, 20],
                'rsi_buy_threshold': [25, 30, 35],
                'rsi_sell_threshold': [65, 70, 75],
                'sma_window': [15, 20, 25]
            },
            'random_forest': {
                'rf_estimators': [50, 100, 200],
                'ml_test_size': [0.15, 0.2, 0.25]
            },
            'quantity': {
                'volume_ma_period': [3, 5, 7],
                'volume_multiplier': [1.1, 1.2, 1.3],
                'stop_profit': [0.015, 0.02, 0.025]
            },
            'bigline': {
                'weights': [
                    [0.4, 0.35, 0.25], 
                    [0.5, 0.3, 0.2], 
                    [0.3, 0.4, 0.3]
                ],
                'ma_short': [3, 5, 7],
                'ma_mid': [15, 20, 25]
            }
        }
    
    def optimize_strategy(self, strategy: StrategyBase, symbol: str, data: Dict[str, Any], 
                         timeframe: str = 'daily', max_workers: int = None) -> Tuple[BacktestResult, Dict[str, Any]]:
        """Optimize strategy parameters using parallel processing"""
        strategy_name = strategy.__class__.__name__.lower().replace('strategy', '').replace('analysis', '')
        param_combinations = self._get_param_combinations(strategy_name)
        
        if not param_combinations:
            # No parameters to optimize, run with default
            result = strategy.backtest(symbol, data, timeframe)
            return result, strategy.params
        
        if max_workers is None:
            max_workers = min(mp.cpu_count(), len(param_combinations))
        
        best_result = BacktestResult()
        best_params = strategy.params
        best_score = -float('inf')
        
        # For small parameter spaces, use threading; for large spaces, use processes
        executor_class = ThreadPoolExecutor if len(param_combinations) <= 10 else ProcessPoolExecutor
        
        try:
            with executor_class(max_workers=max_workers) as executor:
                # Submit all parameter combinations
                futures = []
                for params in param_combinations:
                    future = executor.submit(self._test_params, strategy, symbol, data, timeframe, params)
                    futures.append((future, params))
                
                # Collect results
                for future, params in futures:
                    try:
                        result = future.result(timeout=300)  # 5 minute timeout per test
                        
                        # Score based on Sharpe ratio with drawdown constraint
                        max_drawdown_threshold = self.config.get('strategy_params', {}).get('max_drawdown_threshold', 0.15)
                        if result.max_drawdown < max_drawdown_threshold:
                            score = result.sharpe_ratio
                        else:
                            score = -float('inf')
                        
                        if score > best_score:
                            best_score = score
                            best_result = result
                            best_params = params
                            
                        logger.info(f"{symbol} {strategy_name} params {params}: Sharpe={result.sharpe_ratio:.3f}")
                        
                    except Exception as e:
                        logger.error(f"Parameter test failed for {params}: {e}")
        
        except Exception as e:
            logger.error(f"Parameter optimization failed for {symbol}: {e}")
        
        return best_result, best_params
    
    def _test_params(self, strategy: StrategyBase, symbol: str, data: Dict[str, Any], 
                    timeframe: str, params: Dict[str, Any]) -> BacktestResult:
        """Test a single parameter combination"""
        # Create a copy of the strategy with new parameters
        strategy_copy = deepcopy(strategy)
        strategy_copy.params.update(params)
        return strategy_copy.backtest(symbol, data, timeframe)
    
    def _get_param_combinations(self, strategy_name: str) -> List[Dict[str, Any]]:
        """Generate all parameter combinations for a strategy"""
        params = self.param_grids.get(strategy_name, {})
        if not params:
            return []
        
        keys = list(params.keys())
        values = list(params.values())
        combinations = []
        
        for combination in itertools.product(*values):
            param_dict = dict(zip(keys, combination))
            combinations.append(param_dict)
        
        return combinations

class AIOptimizer:
    """AI-powered strategy selection using Grok API"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.api_key = os.getenv("GROK_API_KEY")
        self.client = None
        
        if XAI_AVAILABLE and self.api_key:
            try:
                self.client = Client(api_key=self.api_key, timeout=3600)
                logger.info("Grok AI optimizer initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Grok client: {e}")
                self.client = None
        else:
            logger.warning("Grok AI optimization not available (missing API key or SDK)")
    
    def optimize_strategy_selection(self, symbol: str, results: Dict[str, BacktestResult], 
                                  timeframe: str = 'daily') -> Dict[str, Any]:
        """Use AI to select the best strategy"""
        if not self.client:
            return self._fallback_optimization(symbol, results, timeframe)
        
        try:
            # Prepare results for AI analysis
            results_dict = {}
            for name, result in results.items():
                results_dict[name] = result.to_dict()
            
            # Determine market index
            symbols_config = self.config.get('symbols', {'tw': [], 'us': []})
            index_symbol = '^TWII' if symbol in symbols_config.get('tw', []) else '^IXIC'
            
            # Create AI chat
            chat = self.client.chat.create(model="grok-3-mini")
            chat.append(system(
                "You are an AI-driven financial strategy optimizer. Analyze strategy backtest results "
                "and select the best strategy based on Sharpe ratio, ensuring max drawdown < 15%. "
                "Consider risk-adjusted returns, consistency, and market conditions."
            ))
            
            max_drawdown_threshold = self.config.get('strategy_params', {}).get('max_drawdown_threshold', 0.15)
            
            prompt = (
                f"為股票 {symbol} 選擇最佳策略（時間框架: {timeframe}，大盤參考: {index_symbol}）。\n"
                f"回測結果：\n{json.dumps(results_dict, ensure_ascii=False, indent=2)}\n\n"
                "選擇標準：\n"
                f"1. 夏普比率最高且最大回撤 < {max_drawdown_threshold}\n"
                "2. 考慮策略一致性和額外指標（如勝率、準確度）\n"
                "3. 評估市場適應性\n\n"
                "請以JSON格式回應：\n"
                "```json\n"
                "{\n"
                f'  "symbol": "{symbol}",\n'
                f'  "analysis_date": "{datetime.today().strftime("%Y-%m-%d")}",\n'
                f'  "index_symbol": "{index_symbol}",\n'
                '  "winning_strategy": {\n'
                '    "name": "strategy_name",\n'
                '    "confidence": 0.85,\n'
                '    "expected_return": 0.12,\n'
                '    "max_drawdown": 0.08,\n'
                '    "sharpe_ratio": 1.45,\n'
                '    "reasoning": "選擇原因說明"\n'
                '  },\n'
                '  "signals": {\n'
                '    "position": "LONG/NEUTRAL/SHORT",\n'
                '    "entry_price": 100.0,\n'
                '    "target_price": 105.0,\n'
                '    "stop_loss": 95.0,\n'
                '    "position_size": 0.5\n'
                '  },\n'
                '  "market_outlook": "簡短市場展望",\n'
                '  "risk_assessment": "風險評估"\n'
                '}\n'
                '```'
            )
            
            chat.append(user(prompt))
            response = chat.sample()
            
            # Parse AI response
            try:
                content = response.content.strip()
                # Extract JSON from markdown code blocks
                if '```json' in content:
                    start = content.find('```json') + 7
                    end = content.find('```', start)
                    json_content = content[start:end].strip()
                else:
                    json_content = content
                
                optimized_result = json.loads(json_content)
                logger.info(f"AI optimization completed for {symbol}")
                return optimized_result
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response: {e}")
                return self._fallback_optimization(symbol, results, timeframe)
        
        except Exception as e:
            logger.error(f"AI optimization failed for {symbol}: {e}")
            return self._fallback_optimization(symbol, results, timeframe)
    
    def _fallback_optimization(self, symbol: str, results: Dict[str, BacktestResult], 
                              timeframe: str = 'daily') -> Dict[str, Any]:
        """Fallback strategy selection without AI"""
        max_drawdown_threshold = self.config.get('strategy_params', {}).get('max_drawdown_threshold', 0.15)
        symbols_config = self.config.get('symbols', {'tw': [], 'us': []})
        index_symbol = '^TWII' if symbol in symbols_config.get('tw', []) else '^IXIC'
        
        best_strategy = 'none'
        best_score = -float('inf')
        best_result = BacktestResult()
        
        # Simple rule-based selection
        for name, result in results.items():
            if result.max_drawdown < max_drawdown_threshold:
                score = result.sharpe_ratio
                if score > best_score:
                    best_score = score
                    best_strategy = name
                    best_result = result
        
        return {
            'symbol': symbol,
            'analysis_date': datetime.today().strftime('%Y-%m-%d'),
            'index_symbol': index_symbol,
            'winning_strategy': {
                'name': best_strategy,
                'confidence': 0.6,  # Lower confidence for rule-based selection
                'expected_return': best_result.expected_return,
                'max_drawdown': best_result.max_drawdown,
                'sharpe_ratio': best_result.sharpe_ratio,
                'reasoning': f'基於夏普比率({best_score:.3f})的規則選擇'
            },
            'signals': best_result.signals,
            'market_outlook': '使用規則化選擇，建議謹慎操作',
            'risk_assessment': '中等風險，請注意資金管理'
        }

class StrategyEngine:
    """Main strategy engine orchestrating all components"""
    
    def __init__(self, config_path: str = 'config.json'):
        # Initialize components
        self.config = ConfigManager(config_path)
        self.data_cache = DataCache()
        
        # Initialize strategies
        self.strategies = {
            'technical': TechnicalAnalysis(self.config),
            'quantity': QuantityStrategy(self.config),
            'random_forest': RandomForestStrategy(self.config),
            'bigline': BigLineStrategy(self.config)
        }
        
        self.optimizer = ParameterOptimizer(self.config)
        self.ai_optimizer = AIOptimizer(self.config)
        self.market_analyst = MarketAnalyst(self.config)
        
        # Setup logging
        if DEPENDENCIES_AVAILABLE:
            log_config = self.config.get('logging', {})
            logger.add(
                log_config.get('file', 'logs/strategy.log'),
                rotation=log_config.get('rotation', '1 MB')
            )
        
        logger.info("Strategy Engine initialized successfully")
    
    def run_strategy_tournament(self, symbol: str, data: Dict[str, Any], 
                              timeframe: str = 'daily', 
                              optimize_params: bool = True,
                              max_workers: int = None) -> Dict[str, Any]:
        """Run comprehensive strategy tournament with optimization"""
        logger.info(f"Starting strategy tournament for {symbol} ({timeframe})")
        
        results = {}
        best_params = {}
        
        # Test each strategy
        for name, strategy in self.strategies.items():
            logger.info(f"Testing {name} strategy for {symbol}")
            
            try:
                if optimize_params:
                    # Optimize parameters
                    result, params = self.optimizer.optimize_strategy(
                        strategy, symbol, data, timeframe, max_workers
                    )
                    best_params[name] = params
                else:
                    # Use default parameters
                    result = strategy.backtest(symbol, data, timeframe)
                    best_params[name] = strategy.params
                
                results[name] = result
                logger.info(f"{name} strategy completed: Sharpe={result.sharpe_ratio:.3f}, "
                           f"Drawdown={result.max_drawdown:.3f}")
                
            except Exception as e:
                logger.error(f"{name} strategy failed for {symbol}: {e}")
                results[name] = BacktestResult()
                best_params[name] = {}
        
        # AI-powered strategy selection
        logger.info(f"Running AI optimization for {symbol}")
        optimized_result = self.ai_optimizer.optimize_strategy_selection(
            symbol, results, timeframe
        )
        
        # Add metadata
        optimized_result['best_parameters'] = best_params
        optimized_result['all_results'] = {name: result.to_dict() for name, result in results.items()}
        
        # Save results
        self._save_results(symbol, optimized_result)
        
        logger.info(f"Strategy tournament completed for {symbol}. "
                   f"Winner: {optimized_result.get('winning_strategy', {}).get('name', 'none')}")
        
        return optimized_result
    
    def batch_analyze_symbols(self, symbols: List[str], timeframe: str = 'daily',
                             optimize_params: bool = True, max_workers: int = None) -> Dict[str, Dict[str, Any]]:
        """Analyze multiple symbols in parallel"""
        logger.info(f"Starting batch analysis for {len(symbols)} symbols")
        
        if max_workers is None:
            max_workers = min(mp.cpu_count(), len(symbols))
        
        results = {}
        
        # Use ThreadPoolExecutor for I/O bound operations
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            
            for symbol in symbols:
                # Prepare dummy data (actual data loaded from cache)
                data = {'symbol': symbol}
                future = executor.submit(
                    self.run_strategy_tournament, 
                    symbol, data, timeframe, optimize_params, 1  # Single worker per symbol
                )
                futures[future] = symbol
            
            # Collect results
            for future in futures:
                symbol = futures[future]
                try:
                    result = future.result(timeout=1800)  # 30 minute timeout per symbol
                    results[symbol] = result
                    logger.info(f"Batch analysis completed for {symbol}")
                except Exception as e:
                    logger.error(f"Batch analysis failed for {symbol}: {e}")
                    results[symbol] = {'error': str(e)}
        
        logger.info(f"Batch analysis completed for {len(results)} symbols")
        return results
    
    def _save_results(self, symbol: str, result: Dict[str, Any]):
        """Save strategy results to file"""
        try:
            strategy_dir = Path(self.config.get('data_paths', {}).get('strategy', 'data/strategy'))
            date_dir = strategy_dir / datetime.today().strftime('%Y-%m-%d')
            date_dir.mkdir(parents=True, exist_ok=True)
            
            # Clean symbol name for filename
            safe_symbol = symbol.replace('^', '').replace('.', '_').replace('/', '_')
            file_path = date_dir / f"{safe_symbol}.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"Results saved to: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save results for {symbol}: {e}")
    
    def get_market_analysis(self, symbol: str, timeframe: str = 'daily') -> Dict[str, Any]:
        """Get comprehensive market analysis"""
        return self.market_analyst.analyze_market(symbol, timeframe)
    
    def clear_cache(self):
        """Clear all cached data"""
        self.data_cache.clear_cache()
        logger.info("Data cache cleared")

# Utility functions for backward compatibility and testing
def create_strategy_engine(config_path: str = 'config.json') -> StrategyEngine:
    """Factory function to create strategy engine"""
    return StrategyEngine(config_path)

def run_single_symbol_analysis(symbol: str, timeframe: str = 'daily', 
                              config_path: str = 'config.json') -> Dict[str, Any]:
    """Quick analysis for a single symbol"""
    engine = create_strategy_engine(config_path)
    data = {'symbol': symbol}  # Dummy data, actual data loaded from cache
    return engine.run_strategy_tournament(symbol, data, timeframe)


