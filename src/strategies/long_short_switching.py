"""
Long-Short Switching Strategy for Futures
Dynamically switches between long and short positions based on trend
"""
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import talib

from .base_strategy import BaseStrategy
from ..exchange.binance_futures_client import BinanceFuturesClient
from ..trading.futures_types import PositionSide


class LongShortSwitchingStrategy(BaseStrategy):
    """
    Long-Short Switching Strategy
    
    Uses multiple timeframe analysis to determine trend direction
    Switches between long and short positions with proper risk management
    """
    
    def __init__(self, config: Dict):
        super().__init__(config)
        
        # Trend detection parameters
        self.fast_ma_period = config.get('fast_ma_period', 20)
        self.slow_ma_period = config.get('slow_ma_period', 50)
        self.trend_strength_period = config.get('trend_strength_period', 14)
        
        # Multi-timeframe settings
        self.timeframes = config.get('timeframes', ['15m', '1h', '4h'])
        self.timeframe_weights = config.get('timeframe_weights', [0.3, 0.4, 0.3])
        
        # Position management
        self.leverage = config.get('leverage', 5)
        self.position_size_pct = config.get('position_size_pct', 0.3)  # 30% of capital
        self.stop_loss_pct = config.get('stop_loss_pct', 0.02)  # 2%
        self.take_profit_pct = config.get('take_profit_pct', 0.06)  # 6%
        self.trailing_stop_pct = config.get('trailing_stop_pct', 0.015)  # 1.5%
        
        # Trend filters
        self.min_trend_strength = config.get('min_trend_strength', 0.6)
        self.volume_confirmation = config.get('volume_confirmation', True)
        self.use_momentum_filter = config.get('use_momentum_filter', True)
        
        # State tracking
        self.current_position = None
        self.entry_price = None
        self.highest_price = None
        self.lowest_price = None
        
    async def analyze(self, exchange: BinanceFuturesClient, symbol: str) -> Dict:
        """Analyze market for long/short opportunity"""
        try:
            # Get multi-timeframe data
            analyses = await self._multi_timeframe_analysis(exchange, symbol)
            
            # Calculate weighted trend direction
            trend_score = self._calculate_trend_score(analyses)
            
            # Get current position
            positions = await asyncio.to_thread(exchange.get_futures_positions, symbol)
            current_position = positions[0] if positions else None
            
            # Determine signal
            signal = self._determine_signal(trend_score, current_position, analyses)
            
            # Get current price for stop/target calculation
            ticker = await asyncio.to_thread(exchange.get_futures_ticker, symbol)
            current_price = ticker['last']
            
            # Calculate stops and targets
            stops_targets = self._calculate_stops_targets(
                signal['direction'], current_price
            )
            
            return {
                'signal': signal['action'],
                'direction': signal['direction'],
                'trend_score': trend_score,
                'current_price': current_price,
                'stop_loss': stops_targets['stop_loss'],
                'take_profit': stops_targets['take_profit'],
                'analyses': analyses,
                'confidence': signal['confidence']
            }
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            return self._no_signal(str(e))
            
    async def _multi_timeframe_analysis(self, exchange: BinanceFuturesClient,
                                      symbol: str) -> Dict:
        """Perform analysis on multiple timeframes"""
        analyses = {}
        
        for timeframe in self.timeframes:
            try:
                # Get OHLCV data
                ohlcv = await asyncio.to_thread(
                    exchange.get_futures_ohlcv,
                    symbol, timeframe, limit=100
                )
                
                # Perform technical analysis
                analysis = self._analyze_timeframe(ohlcv, timeframe)
                analyses[timeframe] = analysis
                
            except Exception as e:
                self.logger.error(f"Failed to analyze {timeframe}: {e}")
                analyses[timeframe] = {'trend': 0, 'strength': 0}
                
        return analyses
        
    def _analyze_timeframe(self, ohlcv: pd.DataFrame, timeframe: str) -> Dict:
        """Analyze a single timeframe"""
        close = ohlcv['close'].values
        high = ohlcv['high'].values
        low = ohlcv['low'].values
        volume = ohlcv['volume'].values
        
        # Moving averages
        fast_ma = talib.EMA(close, timeperiod=self.fast_ma_period)
        slow_ma = talib.EMA(close, timeperiod=self.slow_ma_period)
        
        # Trend direction
        if fast_ma[-1] > slow_ma[-1]:
            trend_direction = 1  # Bullish
        else:
            trend_direction = -1  # Bearish
            
        # Trend strength (ADX)
        adx = talib.ADX(high, low, close, timeperiod=self.trend_strength_period)
        trend_strength = adx[-1] / 100 if not np.isnan(adx[-1]) else 0.5
        
        # Momentum (RSI)
        rsi = talib.RSI(close, timeperiod=14)
        momentum = (rsi[-1] - 50) / 50  # Normalize to -1 to 1
        
        # Volume trend
        volume_ma = talib.SMA(volume, timeperiod=20)
        volume_ratio = volume[-1] / volume_ma[-1] if volume_ma[-1] > 0 else 1
        
        # Price position relative to MA
        price_position = (close[-1] - slow_ma[-1]) / slow_ma[-1]
        
        # MACD
        macd, signal, _ = talib.MACD(close)
        macd_signal = 1 if macd[-1] > signal[-1] else -1
        
        return {
            'trend': trend_direction,
            'strength': trend_strength,
            'momentum': momentum,
            'volume_ratio': volume_ratio,
            'price_position': price_position,
            'macd_signal': macd_signal,
            'fast_ma': fast_ma[-1],
            'slow_ma': slow_ma[-1],
            'rsi': rsi[-1]
        }
        
    def _calculate_trend_score(self, analyses: Dict) -> float:
        """Calculate weighted trend score from multi-timeframe analysis"""
        total_score = 0
        total_weight = 0
        
        for i, timeframe in enumerate(self.timeframes):
            if timeframe in analyses:
                analysis = analyses[timeframe]
                weight = self.timeframe_weights[i]
                
                # Calculate timeframe score
                trend_score = analysis['trend'] * analysis['strength']
                
                # Apply momentum filter if enabled
                if self.use_momentum_filter:
                    trend_score *= (1 + analysis['momentum'] * 0.3)
                    
                # Apply volume confirmation if enabled
                if self.volume_confirmation and analysis['volume_ratio'] > 1.2:
                    trend_score *= 1.1
                    
                total_score += trend_score * weight
                total_weight += weight
                
        return total_score / total_weight if total_weight > 0 else 0
        
    def _determine_signal(self, trend_score: float, current_position: Optional[Dict],
                        analyses: Dict) -> Dict:
        """Determine trading signal based on trend score and current position"""
        # Strong trend thresholds
        strong_long = trend_score > self.min_trend_strength
        strong_short = trend_score < -self.min_trend_strength
        
        # Get highest timeframe analysis for confirmation
        highest_tf = analyses.get(self.timeframes[-1], {})
        
        # No position - look for entry
        if not current_position or current_position['contracts'] == 0:
            if strong_long and highest_tf.get('trend', 0) > 0:
                return {
                    'action': 'open_long',
                    'direction': 'long',
                    'confidence': min(abs(trend_score), 1.0)
                }
            elif strong_short and highest_tf.get('trend', 0) < 0:
                return {
                    'action': 'open_short',
                    'direction': 'short',
                    'confidence': min(abs(trend_score), 1.0)
                }
                
        # Have position - check for switch or exit
        else:
            position_side = 'long' if current_position['contracts'] > 0 else 'short'
            
            # Check if we should switch sides
            if position_side == 'long' and strong_short:
                return {
                    'action': 'switch_to_short',
                    'direction': 'short',
                    'confidence': min(abs(trend_score), 1.0)
                }
            elif position_side == 'short' and strong_long:
                return {
                    'action': 'switch_to_long',
                    'direction': 'long',
                    'confidence': min(abs(trend_score), 1.0)
                }
                
            # Check if trend is weakening (exit signal)
            if abs(trend_score) < self.min_trend_strength * 0.5:
                return {
                    'action': 'close_position',
                    'direction': 'neutral',
                    'confidence': 0.5
                }
                
        return {
            'action': 'hold',
            'direction': 'neutral',
            'confidence': 0
        }
        
    def _calculate_stops_targets(self, direction: str, current_price: float) -> Dict:
        """Calculate stop loss and take profit levels"""
        if direction == 'long':
            stop_loss = current_price * (1 - self.stop_loss_pct)
            take_profit = current_price * (1 + self.take_profit_pct)
        elif direction == 'short':
            stop_loss = current_price * (1 + self.stop_loss_pct)
            take_profit = current_price * (1 - self.take_profit_pct)
        else:
            stop_loss = None
            take_profit = None
            
        return {
            'stop_loss': stop_loss,
            'take_profit': take_profit
        }
        
    async def execute_trade(self, exchange: BinanceFuturesClient,
                          signal: Dict, capital: float) -> Optional[Dict]:
        """Execute long/short switching trade"""
        try:
            action = signal['signal']
            
            if action == 'open_long':
                return await self._open_position(exchange, signal, capital, 'buy')
                
            elif action == 'open_short':
                return await self._open_position(exchange, signal, capital, 'sell')
                
            elif action == 'switch_to_long':
                return await self._switch_position(exchange, signal, capital, 'buy')
                
            elif action == 'switch_to_short':
                return await self._switch_position(exchange, signal, capital, 'sell')
                
            elif action == 'close_position':
                return await self._close_position(exchange, signal)
                
            return None
            
        except Exception as e:
            self.logger.error(f"Trade execution failed: {e}")
            return None
            
    async def _open_position(self, exchange: BinanceFuturesClient,
                           signal: Dict, capital: float, side: str) -> Dict:
        """Open a new position"""
        # Calculate position size
        position_capital = capital * self.position_size_pct
        position_size = await asyncio.to_thread(
            exchange.calculate_futures_position_size,
            self.symbol, position_capital, self.leverage, signal['current_price']
        )
        
        # Set leverage
        await asyncio.to_thread(exchange.set_leverage, self.symbol, self.leverage)
        
        # Create order with stops
        order = await asyncio.to_thread(
            exchange.create_futures_order,
            symbol=self.symbol,
            order_type='market',
            side=side,
            amount=position_size,
            stop_loss=signal.get('stop_loss'),
            take_profit=signal.get('take_profit')
        )
        
        # Update state
        self.current_position = side
        self.entry_price = signal['current_price']
        self.highest_price = self.entry_price if side == 'buy' else None
        self.lowest_price = self.entry_price if side == 'sell' else None
        
        self.logger.info(
            f"Opened {side} position: {position_size} @ {signal['current_price']}"
        )
        
        return {
            'strategy': 'long_short_switching',
            'type': f'open_{signal["direction"]}',
            'order': order,
            'position_size': position_size,
            'leverage': self.leverage,
            'stop_loss': signal.get('stop_loss'),
            'take_profit': signal.get('take_profit')
        }
        
    async def _switch_position(self, exchange: BinanceFuturesClient,
                             signal: Dict, capital: float, new_side: str) -> Dict:
        """Switch from long to short or vice versa"""
        # Close current position
        close_result = await exchange.close_futures_position(self.symbol)
        
        # Open new position in opposite direction
        open_result = await self._open_position(exchange, signal, capital, new_side)
        
        return {
            'strategy': 'long_short_switching',
            'type': f'switch_to_{signal["direction"]}',
            'close_order': close_result,
            'open_order': open_result['order'],
            'new_position': open_result
        }
        
    async def _close_position(self, exchange: BinanceFuturesClient,
                            signal: Dict) -> Dict:
        """Close current position"""
        result = await exchange.close_futures_position(self.symbol)
        
        # Reset state
        self.current_position = None
        self.entry_price = None
        self.highest_price = None
        self.lowest_price = None
        
        return {
            'strategy': 'long_short_switching',
            'type': 'close_position',
            'order': result,
            'reason': 'trend_weakening'
        }
        
    async def update_trailing_stop(self, exchange: BinanceFuturesClient,
                                 current_price: float) -> Optional[Dict]:
        """Update trailing stop for current position"""
        if not self.current_position or not self.entry_price:
            return None
            
        try:
            if self.current_position == 'buy':
                # Update highest price
                if current_price > (self.highest_price or 0):
                    self.highest_price = current_price
                    
                    # Calculate new stop
                    new_stop = self.highest_price * (1 - self.trailing_stop_pct)
                    
                    # Only update if higher than current stop
                    if new_stop > self.entry_price * (1 - self.stop_loss_pct):
                        return await exchange.add_stop_loss(self.symbol, new_stop)
                        
            else:  # short position
                # Update lowest price
                if current_price < (self.lowest_price or float('inf')):
                    self.lowest_price = current_price
                    
                    # Calculate new stop
                    new_stop = self.lowest_price * (1 + self.trailing_stop_pct)
                    
                    # Only update if lower than current stop
                    if new_stop < self.entry_price * (1 + self.stop_loss_pct):
                        return await exchange.add_stop_loss(self.symbol, new_stop)
                        
        except Exception as e:
            self.logger.error(f"Failed to update trailing stop: {e}")
            
        return None
        
    def _no_signal(self, reason: str) -> Dict:
        """Return no signal result"""
        return {
            'signal': 'hold',
            'direction': 'neutral',
            'reason': reason,
            'confidence': 0
        }
        
    def get_parameters(self) -> Dict:
        """Get strategy parameters"""
        return {
            'fast_ma_period': self.fast_ma_period,
            'slow_ma_period': self.slow_ma_period,
            'trend_strength_period': self.trend_strength_period,
            'timeframes': self.timeframes,
            'leverage': self.leverage,
            'position_size_pct': self.position_size_pct,
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct,
            'min_trend_strength': self.min_trend_strength
        }