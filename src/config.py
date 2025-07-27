import os
import json
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration manager for AutoCoin trading bot"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self._load_env_vars()
        self._load_config_file()
        
    def _load_env_vars(self):
        """Load environment variables"""
        # Binance API
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_API_SECRET')
        self.use_testnet = os.getenv('USE_TESTNET', 'true').lower() == 'true'
        
        # Telegram
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        
        # Trading
        self.symbol = os.getenv('TRADING_SYMBOL', 'BTCUSDT')
        self.base_amount = float(os.getenv('BASE_AMOUNT', '1000'))
        self.max_positions = int(os.getenv('MAX_POSITIONS', '1'))
        
        # Validate required fields
        if not self.api_key or not self.api_secret:
            raise ValueError("Binance API credentials not found in environment variables")
            
    def _load_config_file(self):
        """Load configuration from JSON file if it exists"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
                self.strategies = config_data.get('strategies', {})
                self.default_strategy = config_data.get('default_strategy', 'breakout')
        else:
            # Default configuration
            self.strategies = {
                "breakout": {
                    "enabled": True,
                    "lookback_buy": 20,
                    "lookback_sell": 10,
                    "stop_loss": 2.0,
                    "take_profit": 5.0
                },
                "scalping": {
                    "enabled": True,
                    "rsi_period": 14,
                    "rsi_oversold": 30,
                    "rsi_overbought": 70,
                    "bb_period": 20,
                    "bb_std": 2,
                    "stop_loss": 0.5,
                    "take_profit": 1.0
                },
                "trend": {
                    "enabled": True,
                    "ema_fast": 12,
                    "ema_slow": 26,
                    "stop_loss": 3.0,
                    "trailing_stop": 3.0
                }
            }
            self.default_strategy = "breakout"
            
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Get configuration for a specific strategy"""
        return self.strategies.get(strategy_name, {})
        
    def save_config(self):
        """Save current configuration to file"""
        config_data = {
            "default_strategy": self.default_strategy,
            "strategies": self.strategies
        }
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2)