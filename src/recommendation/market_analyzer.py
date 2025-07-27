"""
Market analyzer for identifying current market conditions
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import ta

from ..logger import get_logger

logger = get_logger('market_analyzer')


class MarketCondition(Enum):
    """Market condition types"""
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    BREAKOUT = "BREAKOUT"
    CONSOLIDATING = "CONSOLIDATING"


class TrendStrength(Enum):
    """Trend strength levels"""
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    NONE = "NONE"


class MarketAnalyzer:
    """Analyzes market conditions to recommend appropriate strategies"""
    
    def __init__(self):
        self.analysis_cache: Dict[str, Any] = {}
        self.last_analysis_time: Optional[datetime] = None
        
        # Thresholds for market classification
        self.volatility_threshold_high = 2.5  # % daily volatility
        self.volatility_threshold_low = 0.5
        self.trend_threshold = 0.6  # ADX threshold for trending
        self.range_threshold = 30  # RSI range for ranging market
        
        logger.info("Initialized MarketAnalyzer")
        
    def analyze_market(self, ohlcv_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Comprehensive market analysis
        
        Args:
            ohlcv_data: OHLCV DataFrame with at least 100 candles
            
        Returns:
            Market analysis results
        """
        if len(ohlcv_data) < 100:
            logger.warning(f"Insufficient data for analysis: {len(ohlcv_data)} candles")
            return {}
            
        try:
            # Calculate all indicators
            indicators = self._calculate_indicators(ohlcv_data)
            
            # Analyze different aspects
            trend_analysis = self._analyze_trend(indicators)
            volatility_analysis = self._analyze_volatility(indicators)
            momentum_analysis = self._analyze_momentum(indicators)
            volume_analysis = self._analyze_volume(ohlcv_data, indicators)
            pattern_analysis = self._analyze_patterns(ohlcv_data, indicators)
            
            # Determine overall market condition
            market_condition = self._determine_market_condition(
                trend_analysis,
                volatility_analysis,
                momentum_analysis,
                pattern_analysis
            )
            
            # Compile results
            analysis = {
                'timestamp': datetime.now(),
                'market_condition': market_condition,
                'trend': trend_analysis,
                'volatility': volatility_analysis,
                'momentum': momentum_analysis,
                'volume': volume_analysis,
                'patterns': pattern_analysis,
                'indicators': {
                    'rsi': indicators['rsi'].iloc[-1],
                    'adx': indicators['adx'].iloc[-1],
                    'atr_pct': indicators['atr_pct'].iloc[-1],
                    'bb_width': indicators['bb_width'].iloc[-1]
                }
            }
            
            self.analysis_cache = analysis
            self.last_analysis_time = datetime.now()
            
            logger.info(f"Market analysis complete: {market_condition.value}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing market: {e}")
            return {}
            
    def _calculate_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate technical indicators"""
        indicators = {}
        
        # Price-based
        indicators['sma_20'] = ta.trend.SMAIndicator(data['close'], window=20).sma_indicator()
        indicators['sma_50'] = ta.trend.SMAIndicator(data['close'], window=50).sma_indicator()
        indicators['ema_12'] = ta.trend.EMAIndicator(data['close'], window=12).ema_indicator()
        indicators['ema_26'] = ta.trend.EMAIndicator(data['close'], window=26).ema_indicator()
        
        # Trend
        indicators['adx'] = ta.trend.ADXIndicator(
            data['high'], data['low'], data['close'], window=14
        ).adx()
        indicators['adx_pos'] = ta.trend.ADXIndicator(
            data['high'], data['low'], data['close'], window=14
        ).adx_pos()
        indicators['adx_neg'] = ta.trend.ADXIndicator(
            data['high'], data['low'], data['close'], window=14
        ).adx_neg()
        
        # Momentum
        indicators['rsi'] = ta.momentum.RSIIndicator(data['close'], window=14).rsi()
        macd = ta.trend.MACD(data['close'])
        indicators['macd'] = macd.macd()
        indicators['macd_signal'] = macd.macd_signal()
        indicators['macd_diff'] = macd.macd_diff()
        
        # Volatility
        bb = ta.volatility.BollingerBands(data['close'], window=20, window_dev=2)
        indicators['bb_upper'] = bb.bollinger_hband()
        indicators['bb_middle'] = bb.bollinger_mavg()
        indicators['bb_lower'] = bb.bollinger_lband()
        indicators['bb_width'] = (indicators['bb_upper'] - indicators['bb_lower']) / indicators['bb_middle'] * 100
        
        atr = ta.volatility.AverageTrueRange(data['high'], data['low'], data['close'], window=14)
        indicators['atr'] = atr.average_true_range()
        indicators['atr_pct'] = indicators['atr'] / data['close'] * 100
        
        # Volume
        indicators['volume_sma'] = data['volume'].rolling(window=20).mean()
        indicators['volume_ratio'] = data['volume'] / indicators['volume_sma']
        
        return indicators
        
    def _analyze_trend(self, indicators: Dict[str, pd.Series]) -> Dict[str, Any]:
        """Analyze trend characteristics"""
        current_adx = indicators['adx'].iloc[-1]
        current_adx_pos = indicators['adx_pos'].iloc[-1]
        current_adx_neg = indicators['adx_neg'].iloc[-1]
        
        # Determine trend direction
        if current_adx_pos > current_adx_neg:
            direction = "UP"
        else:
            direction = "DOWN"
            
        # Determine trend strength
        if current_adx > 50:
            strength = TrendStrength.STRONG
        elif current_adx > 25:
            strength = TrendStrength.MODERATE
        elif current_adx > 15:
            strength = TrendStrength.WEAK
        else:
            strength = TrendStrength.NONE
            
        # Moving average alignment
        sma_20 = indicators['sma_20'].iloc[-1]
        sma_50 = indicators['sma_50'].iloc[-1]
        ma_aligned = (sma_20 > sma_50 and direction == "UP") or \
                     (sma_20 < sma_50 and direction == "DOWN")
                     
        return {
            'direction': direction,
            'strength': strength,
            'adx': current_adx,
            'ma_aligned': ma_aligned,
            'is_trending': current_adx > 25
        }
        
    def _analyze_volatility(self, indicators: Dict[str, pd.Series]) -> Dict[str, Any]:
        """Analyze volatility characteristics"""
        current_atr_pct = indicators['atr_pct'].iloc[-1]
        current_bb_width = indicators['bb_width'].iloc[-1]
        
        # Historical volatility
        atr_mean = indicators['atr_pct'].rolling(window=20).mean().iloc[-1]
        atr_std = indicators['atr_pct'].rolling(window=20).std().iloc[-1]
        
        # Volatility level
        if current_atr_pct > self.volatility_threshold_high:
            level = "HIGH"
        elif current_atr_pct < self.volatility_threshold_low:
            level = "LOW"
        else:
            level = "NORMAL"
            
        # Volatility trend
        atr_change = (current_atr_pct - atr_mean) / atr_mean * 100
        if atr_change > 20:
            trend = "INCREASING"
        elif atr_change < -20:
            trend = "DECREASING"
        else:
            trend = "STABLE"
            
        return {
            'level': level,
            'trend': trend,
            'atr_pct': current_atr_pct,
            'bb_width': current_bb_width,
            'relative_volatility': current_atr_pct / atr_mean if atr_mean > 0 else 1
        }
        
    def _analyze_momentum(self, indicators: Dict[str, pd.Series]) -> Dict[str, Any]:
        """Analyze momentum characteristics"""
        current_rsi = indicators['rsi'].iloc[-1]
        current_macd_diff = indicators['macd_diff'].iloc[-1]
        
        # RSI momentum
        if current_rsi > 70:
            rsi_state = "OVERBOUGHT"
        elif current_rsi < 30:
            rsi_state = "OVERSOLD"
        else:
            rsi_state = "NEUTRAL"
            
        # MACD momentum
        macd_trend = "BULLISH" if current_macd_diff > 0 else "BEARISH"
        
        # Momentum strength
        rsi_deviation = abs(current_rsi - 50)
        if rsi_deviation > 30:
            strength = "STRONG"
        elif rsi_deviation > 15:
            strength = "MODERATE"
        else:
            strength = "WEAK"
            
        return {
            'rsi': current_rsi,
            'rsi_state': rsi_state,
            'macd_trend': macd_trend,
            'strength': strength,
            'macd_histogram': current_macd_diff
        }
        
    def _analyze_volume(self, data: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Dict[str, Any]:
        """Analyze volume characteristics"""
        current_volume_ratio = indicators['volume_ratio'].iloc[-1]
        
        # Volume trend
        volume_ma_5 = data['volume'].rolling(window=5).mean().iloc[-1]
        volume_ma_20 = indicators['volume_sma'].iloc[-1]
        
        if volume_ma_5 > volume_ma_20 * 1.2:
            trend = "INCREASING"
        elif volume_ma_5 < volume_ma_20 * 0.8:
            trend = "DECREASING"
        else:
            trend = "STABLE"
            
        # Volume level
        if current_volume_ratio > 2:
            level = "HIGH"
        elif current_volume_ratio < 0.5:
            level = "LOW"
        else:
            level = "NORMAL"
            
        return {
            'trend': trend,
            'level': level,
            'ratio': current_volume_ratio,
            'is_significant': current_volume_ratio > 1.5
        }
        
    def _analyze_patterns(self, data: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Dict[str, Any]:
        """Analyze price patterns"""
        patterns = {
            'breakout': False,
            'consolidation': False,
            'reversal': False
        }
        
        # Check for breakout
        recent_high = data['high'].rolling(window=20).max().iloc[-2]
        recent_low = data['low'].rolling(window=20).min().iloc[-2]
        current_close = data['close'].iloc[-1]
        
        if current_close > recent_high:
            patterns['breakout'] = True
            patterns['breakout_direction'] = "UP"
        elif current_close < recent_low:
            patterns['breakout'] = True
            patterns['breakout_direction'] = "DOWN"
            
        # Check for consolidation
        price_range = (recent_high - recent_low) / recent_low * 100
        if price_range < 5 and indicators['atr_pct'].iloc[-1] < 1:
            patterns['consolidation'] = True
            
        # Check for potential reversal
        rsi = indicators['rsi'].iloc[-1]
        if (rsi > 70 and indicators['macd_diff'].iloc[-1] < 0) or \
           (rsi < 30 and indicators['macd_diff'].iloc[-1] > 0):
            patterns['reversal'] = True
            
        return patterns
        
    def _determine_market_condition(self, 
                                  trend: Dict[str, Any],
                                  volatility: Dict[str, Any],
                                  momentum: Dict[str, Any],
                                  patterns: Dict[str, Any]) -> MarketCondition:
        """Determine overall market condition"""
        
        # Breakout condition
        if patterns.get('breakout'):
            return MarketCondition.BREAKOUT
            
        # Trending conditions
        if trend['is_trending'] and trend['strength'] in [TrendStrength.STRONG, TrendStrength.MODERATE]:
            if trend['direction'] == "UP":
                return MarketCondition.TRENDING_UP
            else:
                return MarketCondition.TRENDING_DOWN
                
        # Consolidating condition
        if patterns.get('consolidation') or volatility['level'] == "LOW":
            return MarketCondition.CONSOLIDATING
            
        # Volatile condition
        if volatility['level'] == "HIGH":
            return MarketCondition.VOLATILE
            
        # Default to ranging
        return MarketCondition.RANGING
        
    def get_market_summary(self) -> str:
        """Get human-readable market summary"""
        if not self.analysis_cache:
            return "No market analysis available"
            
        analysis = self.analysis_cache
        condition = analysis['market_condition']
        trend = analysis['trend']
        volatility = analysis['volatility']
        
        summary = f"Market Condition: {condition.value}\n"
        summary += f"Trend: {trend['direction']} ({trend['strength'].value})\n"
        summary += f"Volatility: {volatility['level']} ({volatility['atr_pct']:.2f}%)\n"
        summary += f"RSI: {analysis['indicators']['rsi']:.2f}\n"
        
        return summary