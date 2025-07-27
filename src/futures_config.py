"""
Extended Configuration for Futures Trading
"""
import os
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from .config import Config

# Load environment variables
load_dotenv()


class FuturesConfig(Config):
    """Extended configuration for futures trading"""
    
    def __init__(self, config_file: str = "futures_config.json"):
        # Initialize base config
        super().__init__()
        
        # Futures-specific config file
        self.futures_config_file = config_file
        
        # Load futures-specific environment variables
        self._load_futures_env_vars()
        
        # Load futures configuration
        self._load_futures_config()
        
        # Risk management defaults
        self.risk_percentage = float(os.getenv('RISK_PERCENTAGE', '2.0'))  # 2% per trade
        
    def _load_futures_env_vars(self):
        """Load futures-specific environment variables"""
        # Futures trading settings
        self.enable_futures = os.getenv('ENABLE_FUTURES', 'false').lower() == 'true'
        self.futures_symbol = os.getenv('FUTURES_SYMBOL', 'BTCUSDT')
        self.default_leverage = int(os.getenv('DEFAULT_LEVERAGE', '5'))
        self.max_leverage = int(os.getenv('MAX_LEVERAGE', '20'))
        
        # Risk management
        self.max_positions_futures = int(os.getenv('MAX_POSITIONS_FUTURES', '3'))
        self.max_position_size_pct = float(os.getenv('MAX_POSITION_SIZE_PCT', '30'))  # 30% of capital
        self.daily_loss_limit = float(os.getenv('DAILY_LOSS_LIMIT', '5'))  # 5% daily loss limit
        self.liquidation_buffer = float(os.getenv('LIQUIDATION_BUFFER', '10'))  # 10% buffer from liquidation
        
        # Margin settings
        self.margin_mode = os.getenv('MARGIN_MODE', 'isolated')  # isolated or cross
        self.hedge_mode = os.getenv('HEDGE_MODE', 'false').lower() == 'true'
        
        # Strategy defaults
        self.default_futures_strategy = os.getenv('DEFAULT_FUTURES_STRATEGY', 'funding_arbitrage')
        
    def _load_futures_config(self):
        """Load futures configuration from file"""
        if os.path.exists(self.futures_config_file):
            with open(self.futures_config_file, 'r') as f:
                config_data = json.load(f)
                self.futures_strategies = config_data.get('futures_strategies', {})
        else:
            # Default futures strategies configuration
            self.futures_strategies = {
                "funding_arbitrage": {
                    "enabled": True,
                    "min_funding_rate": 0.01,  # 1% minimum to enter
                    "funding_threshold": 0.005,  # 0.5% threshold
                    "max_position_size": 0.3,  # 30% of capital
                    "hedge_ratio": 1.0,  # 1:1 hedge with spot
                    "exit_threshold": 0.001,  # 0.1% to exit
                    "leverage": 2,  # Conservative leverage
                    "rebalance_threshold": 0.05  # 5% price deviation
                },
                "grid_trading": {
                    "enabled": True,
                    "grid_levels": 10,  # Number of grid levels
                    "grid_spacing": 0.002,  # 0.2% between levels
                    "grid_size_pct": 0.1,  # 10% of capital per grid
                    "leverage": 3,
                    "use_dynamic_range": True,
                    "range_period": 24,  # Hours for range calculation
                    "range_multiplier": 1.5,  # ATR multiplier
                    "stop_loss_pct": 0.05,  # 5% stop loss
                    "auto_adjust": True  # Auto adjust grid on breakout
                },
                "long_short_switching": {
                    "enabled": True,
                    "fast_ma_period": 20,
                    "slow_ma_period": 50,
                    "trend_strength_period": 14,  # ADX period
                    "timeframes": ["15m", "1h", "4h"],
                    "timeframe_weights": [0.3, 0.4, 0.3],
                    "leverage": 5,
                    "position_size_pct": 0.3,  # 30% of capital
                    "stop_loss_pct": 0.02,  # 2%
                    "take_profit_pct": 0.06,  # 6%
                    "trailing_stop_pct": 0.015,  # 1.5%
                    "min_trend_strength": 0.6,
                    "volume_confirmation": True,
                    "use_momentum_filter": True
                },
                "volatility_breakout": {
                    "enabled": True,
                    "bb_period": 20,  # Bollinger Bands period
                    "bb_std": 2.0,  # Standard deviations
                    "atr_period": 14,
                    "volatility_lookback": 50,
                    "squeeze_threshold": 0.015,  # 1.5% BB width
                    "min_squeeze_bars": 5,  # Minimum squeeze duration
                    "volume_multiplier": 1.5,  # Volume confirmation
                    "momentum_threshold": 60,  # RSI threshold
                    "breakout_candle_size": 1.5,  # x ATR
                    "leverage": 10,  # Higher leverage for breakouts
                    "position_size_pct": 0.2,  # 20% of capital
                    "stop_loss_atr": 1.5,  # 1.5x ATR stop
                    "take_profit_atr": 3.0,  # 3x ATR target
                    "time_stop_hours": 24  # Exit if no profit after 24h
                }
            }
            
    def get_futures_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Get configuration for a specific futures strategy"""
        return self.futures_strategies.get(strategy_name, {})
        
    def update_futures_strategy_config(self, strategy_name: str, params: Dict[str, Any]):
        """Update configuration for a futures strategy"""
        if strategy_name in self.futures_strategies:
            self.futures_strategies[strategy_name].update(params)
            self.save_futures_config()
            
    def save_futures_config(self):
        """Save futures configuration to file"""
        config_data = {
            "default_futures_strategy": self.default_futures_strategy,
            "futures_strategies": self.futures_strategies,
            "risk_settings": {
                "max_positions": self.max_positions_futures,
                "max_position_size_pct": self.max_position_size_pct,
                "daily_loss_limit": self.daily_loss_limit,
                "liquidation_buffer": self.liquidation_buffer,
                "default_leverage": self.default_leverage,
                "max_leverage": self.max_leverage
            },
            "margin_settings": {
                "margin_mode": self.margin_mode,
                "hedge_mode": self.hedge_mode
            }
        }
        
        with open(self.futures_config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
            
    def validate_leverage(self, leverage: int) -> int:
        """Validate and constrain leverage"""
        return max(1, min(leverage, self.max_leverage))
        
    def get_position_size_limit(self, capital: float) -> float:
        """Calculate maximum position size based on capital"""
        return capital * (self.max_position_size_pct / 100)
        
    def get_risk_parameters(self) -> Dict[str, Any]:
        """Get all risk management parameters"""
        return {
            "risk_percentage": self.risk_percentage,
            "max_positions": self.max_positions_futures,
            "max_position_size_pct": self.max_position_size_pct,
            "daily_loss_limit": self.daily_loss_limit,
            "liquidation_buffer": self.liquidation_buffer,
            "default_leverage": self.default_leverage,
            "max_leverage": self.max_leverage,
            "margin_mode": self.margin_mode
        }
        
    def create_example_env_file(self):
        """Create example .env file for futures trading"""
        example_env = """# Futures Trading Configuration

# Enable futures trading
ENABLE_FUTURES=false

# Futures trading symbol
FUTURES_SYMBOL=BTCUSDT

# Leverage settings
DEFAULT_LEVERAGE=5
MAX_LEVERAGE=20

# Risk management
MAX_POSITIONS_FUTURES=3
MAX_POSITION_SIZE_PCT=30
DAILY_LOSS_LIMIT=5
LIQUIDATION_BUFFER=10
RISK_PERCENTAGE=2.0

# Margin settings
MARGIN_MODE=isolated
HEDGE_MODE=false

# Default strategy
DEFAULT_FUTURES_STRATEGY=funding_arbitrage
"""
        
        with open('.env.futures.example', 'w') as f:
            f.write(example_env)
            
        print("Created .env.futures.example file")
        
    def create_example_config_file(self):
        """Create example futures config file"""
        self.save_futures_config()
        print(f"Created {self.futures_config_file} with default configuration")