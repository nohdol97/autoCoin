"""
Scalping Trading Strategy
- Uses RSI and Bollinger Bands for short-term trades
- Buy when RSI < 30 and price touches lower Bollinger Band
- Sell when RSI > 70 and price touches upper Bollinger Band
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import ta

from .base import Strategy, Signal
from ..logger import get_logger

logger = get_logger('scalping_strategy')


class ScalpingStrategy(Strategy):
    """Scalping strategy using RSI and Bollinger Bands"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("scalping", config)
        
        # Strategy specific parameters
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.rsi_overbought = config.get('rsi_overbought', 70)
        
        self.bb_period = config.get('bb_period', 20)
        self.bb_std = config.get('bb_std', 2)
        
        # Override default risk parameters for scalping
        self.stop_loss_pct = config.get('stop_loss', 0.5)  # Tighter stop loss
        self.take_profit_pct = config.get('take_profit', 1.0)  # Smaller profit target
        
        logger.info(f"Scalping strategy initialized: "
                   f"RSI({self.rsi_period}), BB({self.bb_period},{self.bb_std})")
        
    def get_required_candles(self) -> int:
        """Need enough candles for indicators"""
        return max(self.rsi_period, self.bb_period) + 5
        
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate RSI and Bollinger Bands"""
        # RSI
        data['rsi'] = ta.momentum.RSIIndicator(
            close=data['close'],
            window=self.rsi_period
        ).rsi()
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(
            close=data['close'],
            window=self.bb_period,
            window_dev=self.bb_std
        )
        data['bb_upper'] = bb.bollinger_hband()
        data['bb_middle'] = bb.bollinger_mavg()
        data['bb_lower'] = bb.bollinger_lband()
        
        return data
        
    def analyze(self, data: pd.DataFrame, current_price: float) -> Signal:
        """
        Analyze market data for scalping signals
        
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
        current_rsi = df['rsi'].iloc[-1]
        current_bb_upper = df['bb_upper'].iloc[-1]
        current_bb_lower = df['bb_lower'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        
        logger.debug(f"Current: ${current_price:.2f}, RSI: {current_rsi:.2f}, "
                    f"BB Upper: ${current_bb_upper:.2f}, BB Lower: ${current_bb_lower:.2f}")
        
        # Generate signals
        if self.position is None:
            # Look for entry signal
            # Buy when oversold and touching lower band
            if (current_rsi < self.rsi_oversold and 
                current_price <= current_bb_lower and
                prev_close > current_bb_lower):
                logger.info(f"BUY signal: RSI={current_rsi:.2f} < {self.rsi_oversold} "
                           f"and price touched lower BB ${current_bb_lower:.2f}")
                return Signal.BUY
                
        else:
            # Look for exit signal
            # Sell when overbought and touching upper band
            if (current_rsi > self.rsi_overbought and 
                current_price >= current_bb_upper and
                prev_close < current_bb_upper):
                logger.info(f"SELL signal: RSI={current_rsi:.2f} > {self.rsi_overbought} "
                           f"and price touched upper BB ${current_bb_upper:.2f}")
                return Signal.SELL
                
            # Also check if RSI reverses from extreme levels (optional exit)
            if self.position.side == "LONG" and current_rsi > 70:
                logger.info(f"SELL signal: RSI={current_rsi:.2f} > 70 (overbought exit)")
                return Signal.SELL
            elif self.position.side == "SHORT" and current_rsi < 30:
                logger.info(f"SELL signal: RSI={current_rsi:.2f} < 30 (oversold exit)")
                return Signal.SELL
                
        return Signal.HOLD
        
    def backtest(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Backtest the scalping strategy
        
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
        
        for i in range(self.get_required_candles(), len(df)):
            current_price = df['close'].iloc[i]
            prev_close = df['close'].iloc[i-1]
            current_rsi = df['rsi'].iloc[i]
            current_bb_upper = df['bb_upper'].iloc[i]
            current_bb_lower = df['bb_lower'].iloc[i]
            
            if not in_position:
                # Check for buy signal
                if (current_rsi < self.rsi_oversold and 
                    current_price <= current_bb_lower and
                    prev_close > current_bb_lower):
                    df.loc[df.index[i], 'signal'] = 'BUY'
                    df.loc[df.index[i], 'position'] = 1
                    in_position = True
            else:
                # Check for sell signal
                if (current_rsi > self.rsi_overbought and 
                    current_price >= current_bb_upper and
                    prev_close < current_bb_upper) or current_rsi > 70:
                    df.loc[df.index[i], 'signal'] = 'SELL'
                    df.loc[df.index[i], 'position'] = 0
                    in_position = False
                else:
                    df.loc[df.index[i], 'position'] = 1
                    
        # Calculate returns
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['position'].shift(1) * df['returns']
        df['cumulative_returns'] = (1 + df['returns']).cumprod()
        df['cumulative_strategy_returns'] = (1 + df['strategy_returns']).cumprod()
        
        return df