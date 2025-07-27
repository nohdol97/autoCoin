"""
Breakout Trading Strategy
- Buy when price breaks above 20-day high
- Sell when price breaks below 10-day low
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

from .base import Strategy, Signal
from ..logger import get_logger

logger = get_logger('breakout_strategy')


class BreakoutStrategy(Strategy):
    """Breakout trading strategy implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("breakout", config)
        
        # Strategy specific parameters
        self.lookback_buy = config.get('lookback_buy', 20)  # days for buy signal
        self.lookback_sell = config.get('lookback_sell', 10)  # days for sell signal
        
        logger.info(f"Breakout strategy initialized: "
                   f"buy={self.lookback_buy} days, sell={self.lookback_sell} days")
        
    def get_required_candles(self) -> int:
        """Need enough candles for the longest lookback period"""
        return max(self.lookback_buy, self.lookback_sell) + 1
        
    def analyze(self, data: pd.DataFrame, current_price: float) -> Signal:
        """
        Analyze market data for breakout signals
        
        Args:
            data: Historical OHLCV data with columns: timestamp, open, high, low, close, volume
            current_price: Current market price
            
        Returns:
            Trading signal
        """
        if len(data) < self.get_required_candles():
            logger.warning(f"Insufficient data: {len(data)} candles, need {self.get_required_candles()}")
            return Signal.HOLD
            
        # Calculate rolling highs and lows
        high_20 = data['high'].rolling(window=self.lookback_buy).max()
        low_10 = data['low'].rolling(window=self.lookback_sell).min()
        
        # Get the most recent values (excluding current candle)
        prev_high_20 = high_20.iloc[-2]
        prev_low_10 = low_10.iloc[-2]
        
        # Get previous close
        prev_close = data['close'].iloc[-2]
        
        logger.debug(f"Current: ${current_price:.2f}, "
                    f"20d High: ${prev_high_20:.2f}, "
                    f"10d Low: ${prev_low_10:.2f}")
        
        # Generate signals
        if self.position is None:
            # Look for entry signal
            if current_price > prev_high_20 and prev_close <= prev_high_20:
                logger.info(f"BUY signal: Price ${current_price:.2f} broke above "
                           f"20-day high ${prev_high_20:.2f}")
                return Signal.BUY
                
        else:
            # Look for exit signal if we have a position
            if current_price < prev_low_10 and prev_close >= prev_low_10:
                logger.info(f"SELL signal: Price ${current_price:.2f} broke below "
                           f"10-day low ${prev_low_10:.2f}")
                return Signal.SELL
                
        return Signal.HOLD
        
    def backtest(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Backtest the strategy on historical data
        
        Args:
            data: Historical OHLCV data
            
        Returns:
            DataFrame with signals and performance
        """
        if len(data) < self.get_required_candles():
            raise ValueError(f"Insufficient data for backtesting")
            
        # Calculate indicators
        data['high_20'] = data['high'].rolling(window=self.lookback_buy).max()
        data['low_10'] = data['low'].rolling(window=self.lookback_sell).min()
        
        # Initialize signals
        data['signal'] = 'HOLD'
        data['position'] = 0
        
        # Generate signals
        in_position = False
        
        for i in range(self.get_required_candles(), len(data)):
            current_price = data['close'].iloc[i]
            prev_close = data['close'].iloc[i-1]
            prev_high_20 = data['high_20'].iloc[i-1]
            prev_low_10 = data['low_10'].iloc[i-1]
            
            if not in_position:
                # Check for buy signal
                if current_price > prev_high_20 and prev_close <= prev_high_20:
                    data.loc[data.index[i], 'signal'] = 'BUY'
                    data.loc[data.index[i], 'position'] = 1
                    in_position = True
            else:
                # Check for sell signal
                if current_price < prev_low_10 and prev_close >= prev_low_10:
                    data.loc[data.index[i], 'signal'] = 'SELL'
                    data.loc[data.index[i], 'position'] = 0
                    in_position = False
                else:
                    data.loc[data.index[i], 'position'] = 1
                    
        # Calculate returns
        data['returns'] = data['close'].pct_change()
        data['strategy_returns'] = data['position'].shift(1) * data['returns']
        data['cumulative_returns'] = (1 + data['returns']).cumprod()
        data['cumulative_strategy_returns'] = (1 + data['strategy_returns']).cumprod()
        
        return data