"""
Volatility Breakout Strategy for Futures
Trades breakouts from periods of low volatility
"""
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import talib

from .base_strategy import BaseStrategy
from ..exchange.binance_futures_client import BinanceFuturesClient


class VolatilityBreakoutStrategy(BaseStrategy):
    """
    Volatility Breakout Strategy
    
    Identifies periods of low volatility (consolidation)
    Trades breakouts with high leverage when volatility expands
    """
    
    def __init__(self, config: Dict):
        super().__init__(config)
        
        # Volatility parameters
        self.bb_period = config.get('bb_period', 20)  # Bollinger Bands period
        self.bb_std = config.get('bb_std', 2.0)  # Standard deviations
        self.atr_period = config.get('atr_period', 14)  # ATR period
        self.volatility_lookback = config.get('volatility_lookback', 50)
        
        # Squeeze detection
        self.squeeze_threshold = config.get('squeeze_threshold', 0.015)  # 1.5%
        self.min_squeeze_bars = config.get('min_squeeze_bars', 5)
        
        # Breakout confirmation
        self.volume_multiplier = config.get('volume_multiplier', 1.5)
        self.momentum_threshold = config.get('momentum_threshold', 60)  # RSI
        self.breakout_candle_size = config.get('breakout_candle_size', 1.5)  # x ATR
        
        # Position management
        self.leverage = config.get('leverage', 10)  # Higher for breakouts
        self.position_size_pct = config.get('position_size_pct', 0.2)  # 20%
        self.stop_loss_atr = config.get('stop_loss_atr', 1.5)  # 1.5x ATR
        self.take_profit_atr = config.get('take_profit_atr', 3.0)  # 3x ATR
        self.time_stop_hours = config.get('time_stop_hours', 24)  # Exit if no profit
        
        # State tracking
        self.squeeze_count = 0
        self.entry_time = None
        self.breakout_high = None
        self.breakout_low = None
        
    async def analyze(self, exchange: BinanceFuturesClient, symbol: str) -> Dict:
        """Analyze market for volatility breakout"""
        try:
            # Get OHLCV data
            ohlcv = await asyncio.to_thread(
                exchange.get_futures_ohlcv,
                symbol, '1h', limit=100
            )
            
            # Calculate indicators
            indicators = self._calculate_indicators(ohlcv)
            
            # Detect squeeze condition
            is_squeeze, squeeze_data = self._detect_squeeze(indicators, ohlcv)
            
            # Check for breakout
            breakout_signal = self._check_breakout(indicators, ohlcv, squeeze_data)
            
            # Get current price
            ticker = await asyncio.to_thread(exchange.get_futures_ticker, symbol)
            current_price = ticker['last']
            
            # Calculate stops and targets if breakout
            if breakout_signal['signal'] in ['long_breakout', 'short_breakout']:
                stops_targets = self._calculate_stops_targets(
                    breakout_signal['direction'],
                    current_price,
                    indicators['atr']
                )
            else:
                stops_targets = {'stop_loss': None, 'take_profit': None}
                
            return {
                'signal': breakout_signal['signal'],
                'direction': breakout_signal['direction'],
                'current_price': current_price,
                'stop_loss': stops_targets['stop_loss'],
                'take_profit': stops_targets['take_profit'],
                'squeeze_count': self.squeeze_count,
                'volatility_percentile': indicators['volatility_percentile'],
                'breakout_strength': breakout_signal.get('strength', 0),
                'confidence': breakout_signal['confidence']
            }
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            return self._no_signal(str(e))
            
    def _calculate_indicators(self, ohlcv: pd.DataFrame) -> Dict:
        """Calculate technical indicators"""
        close = ohlcv['close'].values
        high = ohlcv['high'].values
        low = ohlcv['low'].values
        volume = ohlcv['volume'].values
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = talib.BBANDS(
            close, timeperiod=self.bb_period, nbdevup=self.bb_std, nbdevdn=self.bb_std
        )
        
        # ATR
        atr = talib.ATR(high, low, close, timeperiod=self.atr_period)
        
        # Keltner Channels (for squeeze detection)
        kc_middle = talib.EMA(close, timeperiod=20)
        kc_range = talib.ATR(high, low, close, timeperiod=20) * 1.5
        kc_upper = kc_middle + kc_range
        kc_lower = kc_middle - kc_range
        
        # RSI
        rsi = talib.RSI(close, timeperiod=14)
        
        # Volume analysis
        volume_ma = talib.SMA(volume, timeperiod=20)
        
        # Historical volatility
        returns = pd.Series(close).pct_change()
        historical_vol = returns.rolling(self.volatility_lookback).std()
        current_vol = historical_vol.iloc[-1]
        vol_percentile = (historical_vol < current_vol).sum() / len(historical_vol)
        
        # Momentum
        momentum = talib.MOM(close, timeperiod=10)
        
        return {
            'bb_upper': bb_upper,
            'bb_middle': bb_middle,
            'bb_lower': bb_lower,
            'bb_width': (bb_upper - bb_lower) / bb_middle,
            'kc_upper': kc_upper,
            'kc_lower': kc_lower,
            'atr': atr[-1],
            'atr_series': atr,
            'rsi': rsi[-1],
            'volume': volume[-1],
            'volume_ma': volume_ma[-1],
            'volume_ratio': volume[-1] / volume_ma[-1] if volume_ma[-1] > 0 else 1,
            'volatility_percentile': vol_percentile,
            'momentum': momentum[-1]
        }
        
    def _detect_squeeze(self, indicators: Dict, ohlcv: pd.DataFrame) -> Tuple[bool, Dict]:
        """Detect Bollinger Band squeeze (low volatility)"""
        # BB squeeze: Bollinger Bands inside Keltner Channels
        bb_width = indicators['bb_width']
        current_squeeze = bb_width[-1] < self.squeeze_threshold
        
        # Count consecutive squeeze bars
        squeeze_bars = 0
        for i in range(len(bb_width) - 1, -1, -1):
            if bb_width[i] < self.squeeze_threshold:
                squeeze_bars += 1
            else:
                break
                
        # Update state
        if current_squeeze:
            self.squeeze_count = squeeze_bars
        else:
            if self.squeeze_count >= self.min_squeeze_bars:
                # Squeeze just ended - potential breakout
                pass
            self.squeeze_count = 0
            
        # Calculate squeeze intensity
        avg_bb_width = np.mean(bb_width[-20:])
        squeeze_intensity = 1 - (bb_width[-1] / avg_bb_width) if avg_bb_width > 0 else 0
        
        return current_squeeze, {
            'squeeze_bars': squeeze_bars,
            'squeeze_intensity': squeeze_intensity,
            'bb_width': bb_width[-1],
            'ready_for_breakout': squeeze_bars >= self.min_squeeze_bars
        }
        
    def _check_breakout(self, indicators: Dict, ohlcv: pd.DataFrame,
                       squeeze_data: Dict) -> Dict:
        """Check for volatility breakout"""
        close = ohlcv['close'].values
        high = ohlcv['high'].values
        low = ohlcv['low'].values
        
        # No breakout if still in squeeze
        if self.squeeze_count > 0 and self.squeeze_count < self.min_squeeze_bars:
            return {
                'signal': 'hold',
                'direction': 'neutral',
                'confidence': 0,
                'reason': 'building_squeeze'
            }
            
        # Check for breakout conditions
        current_close = close[-1]
        prev_close = close[-2]
        
        # Breakout above upper band
        if current_close > indicators['bb_upper'][-1] and prev_close <= indicators['bb_upper'][-2]:
            if self._confirm_breakout('long', indicators, ohlcv):
                return {
                    'signal': 'long_breakout',
                    'direction': 'long',
                    'strength': self._calculate_breakout_strength('long', indicators, ohlcv),
                    'confidence': self._calculate_confidence('long', indicators, squeeze_data)
                }
                
        # Breakout below lower band
        elif current_close < indicators['bb_lower'][-1] and prev_close >= indicators['bb_lower'][-2]:
            if self._confirm_breakout('short', indicators, ohlcv):
                return {
                    'signal': 'short_breakout',
                    'direction': 'short',
                    'strength': self._calculate_breakout_strength('short', indicators, ohlcv),
                    'confidence': self._calculate_confidence('short', indicators, squeeze_data)
                }
                
        # Check for failed breakout (exit signal)
        if self.entry_time:
            hours_since_entry = (datetime.now() - self.entry_time).total_seconds() / 3600
            if hours_since_entry > self.time_stop_hours:
                return {
                    'signal': 'exit_timeout',
                    'direction': 'neutral',
                    'confidence': 0.8,
                    'reason': 'time_stop'
                }
                
        return {
            'signal': 'hold',
            'direction': 'neutral',
            'confidence': 0
        }
        
    def _confirm_breakout(self, direction: str, indicators: Dict,
                         ohlcv: pd.DataFrame) -> bool:
        """Confirm breakout with additional filters"""
        # Volume confirmation
        if indicators['volume_ratio'] < self.volume_multiplier:
            return False
            
        # Momentum confirmation
        if direction == 'long':
            if indicators['rsi'] < self.momentum_threshold:
                return False
        else:  # short
            if indicators['rsi'] > (100 - self.momentum_threshold):
                return False
                
        # Candle size confirmation
        current_range = ohlcv['high'].iloc[-1] - ohlcv['low'].iloc[-1]
        if current_range < indicators['atr'] * self.breakout_candle_size:
            return False
            
        return True
        
    def _calculate_breakout_strength(self, direction: str, indicators: Dict,
                                   ohlcv: pd.DataFrame) -> float:
        """Calculate breakout strength score"""
        close = ohlcv['close'].values
        
        # Price distance from band
        if direction == 'long':
            distance = (close[-1] - indicators['bb_upper'][-1]) / indicators['atr']
        else:
            distance = (indicators['bb_lower'][-1] - close[-1]) / indicators['atr']
            
        # Volume strength
        volume_strength = min(indicators['volume_ratio'] / 2, 1.0)
        
        # Momentum strength
        momentum_strength = abs(indicators['momentum']) / indicators['atr']
        
        # Combined strength
        strength = (distance * 0.4 + volume_strength * 0.3 + momentum_strength * 0.3)
        
        return min(strength, 1.0)
        
    def _calculate_confidence(self, direction: str, indicators: Dict,
                            squeeze_data: Dict) -> float:
        """Calculate confidence score for breakout"""
        confidence = 0
        
        # Squeeze quality (longer squeeze = higher confidence)
        if squeeze_data['ready_for_breakout']:
            confidence += min(squeeze_data['squeeze_bars'] / 10, 0.3)
            
        # Low volatility percentile (lower = better)
        confidence += (1 - indicators['volatility_percentile']) * 0.3
        
        # Volume confirmation
        if indicators['volume_ratio'] > self.volume_multiplier:
            confidence += 0.2
            
        # RSI confirmation
        if direction == 'long' and indicators['rsi'] > self.momentum_threshold:
            confidence += 0.2
        elif direction == 'short' and indicators['rsi'] < (100 - self.momentum_threshold):
            confidence += 0.2
            
        return min(confidence, 1.0)
        
    def _calculate_stops_targets(self, direction: str, current_price: float,
                               atr: float) -> Dict:
        """Calculate stop loss and take profit based on ATR"""
        if direction == 'long':
            stop_loss = current_price - (atr * self.stop_loss_atr)
            take_profit = current_price + (atr * self.take_profit_atr)
        elif direction == 'short':
            stop_loss = current_price + (atr * self.stop_loss_atr)
            take_profit = current_price - (atr * self.take_profit_atr)
        else:
            stop_loss = None
            take_profit = None
            
        return {
            'stop_loss': stop_loss,
            'take_profit': take_profit
        }
        
    async def execute_trade(self, exchange: BinanceFuturesClient,
                          signal: Dict, capital: float) -> Optional[Dict]:
        """Execute volatility breakout trade"""
        try:
            if signal['signal'] == 'long_breakout':
                return await self._open_breakout_position(
                    exchange, signal, capital, 'buy'
                )
                
            elif signal['signal'] == 'short_breakout':
                return await self._open_breakout_position(
                    exchange, signal, capital, 'sell'
                )
                
            elif signal['signal'] == 'exit_timeout':
                return await self._exit_position(exchange, signal)
                
            return None
            
        except Exception as e:
            self.logger.error(f"Trade execution failed: {e}")
            return None
            
    async def _open_breakout_position(self, exchange: BinanceFuturesClient,
                                    signal: Dict, capital: float, side: str) -> Dict:
        """Open a breakout position with tight risk management"""
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
            stop_loss=signal['stop_loss'],
            take_profit=signal['take_profit']
        )
        
        # Update state
        self.entry_time = datetime.now()
        self.breakout_high = signal['current_price'] if side == 'buy' else None
        self.breakout_low = signal['current_price'] if side == 'sell' else None
        
        self.logger.info(
            f"Opened breakout {side} position: {position_size} @ {signal['current_price']} "
            f"with {self.leverage}x leverage"
        )
        
        return {
            'strategy': 'volatility_breakout',
            'type': f'{signal["direction"]}_breakout',
            'order': order,
            'position_size': position_size,
            'leverage': self.leverage,
            'stop_loss': signal['stop_loss'],
            'take_profit': signal['take_profit'],
            'breakout_strength': signal.get('breakout_strength', 0)
        }
        
    async def _exit_position(self, exchange: BinanceFuturesClient,
                           signal: Dict) -> Dict:
        """Exit position due to timeout or other reasons"""
        result = await exchange.close_futures_position(self.symbol)
        
        # Reset state
        self.entry_time = None
        self.breakout_high = None
        self.breakout_low = None
        self.squeeze_count = 0
        
        return {
            'strategy': 'volatility_breakout',
            'type': 'exit',
            'order': result,
            'reason': signal.get('reason', 'manual_exit')
        }
        
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
            'bb_period': self.bb_period,
            'bb_std': self.bb_std,
            'atr_period': self.atr_period,
            'squeeze_threshold': self.squeeze_threshold,
            'min_squeeze_bars': self.min_squeeze_bars,
            'leverage': self.leverage,
            'position_size_pct': self.position_size_pct,
            'stop_loss_atr': self.stop_loss_atr,
            'take_profit_atr': self.take_profit_atr
        }