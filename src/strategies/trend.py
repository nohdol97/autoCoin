"""
Trend Following Strategy
- Uses EMA crossover for trend detection
- Buy when fast EMA crosses above slow EMA
- Sell when fast EMA crosses below slow EMA
- Includes trailing stop loss
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import ta

from .base import Strategy, Signal
from ..logger import get_logger

logger = get_logger('trend_strategy')


class TrendFollowingStrategy(Strategy):
    """Trend following strategy using EMA crossover"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("trend", config)
        
        # Strategy specific parameters
        self.ema_fast = config.get('ema_fast', 12)
        self.ema_slow = config.get('ema_slow', 26)
        self.trailing_stop_pct = config.get('trailing_stop', 3.0)
        
        # Trend following typically uses wider stops
        self.stop_loss_pct = config.get('stop_loss', 3.0)
        self.take_profit_pct = config.get('take_profit', 10.0)  # Let profits run
        
        # Trailing stop tracking
        self.highest_price = None
        self.trailing_stop_price = None
        
        logger.info(f"Trend following strategy initialized: "
                   f"EMA({self.ema_fast}/{self.ema_slow}), "
                   f"Trailing stop: {self.trailing_stop_pct}%")
        
    def get_required_candles(self) -> int:
        """Need enough candles for slow EMA"""
        return self.ema_slow + 10
        
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate EMAs and signals"""
        # Calculate EMAs
        data['ema_fast'] = ta.trend.EMAIndicator(
            close=data['close'],
            window=self.ema_fast
        ).ema_indicator()
        
        data['ema_slow'] = ta.trend.EMAIndicator(
            close=data['close'],
            window=self.ema_slow
        ).ema_indicator()
        
        # Calculate MACD for additional confirmation
        macd = ta.trend.MACD(
            close=data['close'],
            window_slow=self.ema_slow,
            window_fast=self.ema_fast,
            window_sign=9
        )
        data['macd'] = macd.macd()
        data['macd_signal'] = macd.macd_signal()
        data['macd_diff'] = macd.macd_diff()
        
        return data
        
    def update_trailing_stop(self, current_price: float):
        """Update trailing stop for open position"""
        if not self.position or self.position.side != "LONG":
            return
            
        # Initialize or update highest price
        if self.highest_price is None or current_price > self.highest_price:
            self.highest_price = current_price
            self.trailing_stop_price = current_price * (1 - self.trailing_stop_pct / 100)
            logger.debug(f"Updated trailing stop: ${self.trailing_stop_price:.2f} "
                        f"(High: ${self.highest_price:.2f})")
            
    def check_exit_conditions(self, current_price: float) -> Optional[str]:
        """Check exit conditions including trailing stop"""
        # First check regular stop loss and take profit
        exit_reason = super().check_exit_conditions(current_price)
        if exit_reason:
            return exit_reason
            
        # Check trailing stop
        if (self.position and 
            self.position.side == "LONG" and 
            self.trailing_stop_price and 
            current_price <= self.trailing_stop_price):
            return "TRAILING_STOP"
            
        return None
        
    def analyze(self, data: pd.DataFrame, current_price: float) -> Signal:
        """
        Analyze market data for trend signals
        
        Args:
            data: Historical OHLCV data
            current_price: Current market price
            
        Returns:
            Trading signal
        """
        if len(data) < self.get_required_candles():
            logger.warning(f"Insufficient data: {len(data)} candles, need {self.get_required_candles()}")
            return Signal.HOLD
            
        # Calculate indicators
        df = self.calculate_indicators(data.copy())
        
        # Get latest values
        current_ema_fast = df['ema_fast'].iloc[-1]
        current_ema_slow = df['ema_slow'].iloc[-1]
        prev_ema_fast = df['ema_fast'].iloc[-2]
        prev_ema_slow = df['ema_slow'].iloc[-2]
        current_macd_diff = df['macd_diff'].iloc[-1]
        
        logger.debug(f"Current: ${current_price:.2f}, "
                    f"EMA Fast: ${current_ema_fast:.2f}, "
                    f"EMA Slow: ${current_ema_slow:.2f}, "
                    f"MACD Diff: {current_macd_diff:.4f}")
        
        # Update trailing stop if in position
        if self.position:
            self.update_trailing_stop(current_price)
        
        # Generate signals
        if self.position is None:
            # Look for entry signal - Golden Cross
            if (prev_ema_fast <= prev_ema_slow and 
                current_ema_fast > current_ema_slow and
                current_macd_diff > 0):
                logger.info(f"BUY signal: EMA Golden Cross detected, "
                           f"Fast EMA ${current_ema_fast:.2f} > Slow EMA ${current_ema_slow:.2f}")
                # Reset trailing stop variables
                self.highest_price = None
                self.trailing_stop_price = None
                return Signal.BUY
                
        else:
            # Look for exit signal - Death Cross
            if (prev_ema_fast >= prev_ema_slow and 
                current_ema_fast < current_ema_slow):
                logger.info(f"SELL signal: EMA Death Cross detected, "
                           f"Fast EMA ${current_ema_fast:.2f} < Slow EMA ${current_ema_slow:.2f}")
                return Signal.SELL
                
            # Check trailing stop
            exit_reason = self.check_exit_conditions(current_price)
            if exit_reason == "TRAILING_STOP":
                logger.info(f"SELL signal: Trailing stop hit at ${self.trailing_stop_price:.2f}")
                return Signal.SELL
                
        return Signal.HOLD
        
    def backtest(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Backtest the trend following strategy
        
        Args:
            data: Historical OHLCV data
            
        Returns:
            DataFrame with signals and performance
        """
        if len(data) < self.get_required_candles():
            raise ValueError(f"Insufficient data for backtesting")
            
        # Calculate indicators
        df = self.calculate_indicators(data.copy())
        
        # Initialize signals
        df['signal'] = 'HOLD'
        df['position'] = 0
        
        # Generate signals
        in_position = False
        highest_price = None
        trailing_stop = None
        
        for i in range(self.get_required_candles(), len(df)):
            current_price = df['close'].iloc[i]
            current_ema_fast = df['ema_fast'].iloc[i]
            current_ema_slow = df['ema_slow'].iloc[i]
            prev_ema_fast = df['ema_fast'].iloc[i-1]
            prev_ema_slow = df['ema_slow'].iloc[i-1]
            current_macd_diff = df['macd_diff'].iloc[i]
            
            if not in_position:
                # Check for buy signal
                if (prev_ema_fast <= prev_ema_slow and 
                    current_ema_fast > current_ema_slow and
                    current_macd_diff > 0):
                    df.loc[df.index[i], 'signal'] = 'BUY'
                    df.loc[df.index[i], 'position'] = 1
                    in_position = True
                    highest_price = current_price
                    trailing_stop = current_price * (1 - self.trailing_stop_pct / 100)
            else:
                # Update trailing stop
                if current_price > highest_price:
                    highest_price = current_price
                    trailing_stop = current_price * (1 - self.trailing_stop_pct / 100)
                
                # Check for sell signal
                if ((prev_ema_fast >= prev_ema_slow and current_ema_fast < current_ema_slow) or
                    (trailing_stop and current_price <= trailing_stop)):
                    df.loc[df.index[i], 'signal'] = 'SELL'
                    df.loc[df.index[i], 'position'] = 0
                    in_position = False
                    highest_price = None
                    trailing_stop = None
                else:
                    df.loc[df.index[i], 'position'] = 1
                    
        # Calculate returns
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['position'].shift(1) * df['returns']
        df['cumulative_returns'] = (1 + df['returns']).cumprod()
        df['cumulative_strategy_returns'] = (1 + df['strategy_returns']).cumprod()
        
        return df
        
    def reset(self):
        """Reset strategy state including trailing stop"""
        super().reset()
        self.highest_price = None
        self.trailing_stop_price = None