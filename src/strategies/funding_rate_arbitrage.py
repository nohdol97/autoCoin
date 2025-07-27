"""
Funding Rate Arbitrage Strategy
Exploits funding rate differences between spot and futures markets
"""
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from decimal import Decimal

from .base_strategy import BaseStrategy
from ..trading.futures_types import FundingRate, PositionSide
from ..exchange.binance_futures_client import BinanceFuturesClient


class FundingRateArbitrageStrategy(BaseStrategy):
    """
    Funding Rate Arbitrage Strategy
    
    When funding rate is positive (longs pay shorts):
    - Short futures
    - Buy spot (hedge)
    
    When funding rate is negative (shorts pay longs):
    - Long futures
    - Sell spot (if held)
    """
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.min_funding_rate = config.get('min_funding_rate', 0.01)  # 1% minimum
        self.funding_threshold = config.get('funding_threshold', 0.005)  # 0.5%
        self.max_position_size = config.get('max_position_size', 0.3)  # 30% of capital
        self.hedge_ratio = config.get('hedge_ratio', 1.0)  # 1:1 hedge
        self.exit_threshold = config.get('exit_threshold', 0.001)  # 0.1%
        self.leverage = config.get('leverage', 2)  # Conservative leverage
        
        # Track positions
        self.futures_position = None
        self.spot_position = None
        self.entry_funding_rate = None
        
    async def analyze(self, exchange: BinanceFuturesClient, symbol: str) -> Dict:
        """Analyze funding rate opportunity"""
        try:
            # Get funding rate
            funding = await exchange.get_funding_rate(symbol)
            if not funding:
                return self._no_signal("Failed to get funding rate")
                
            # Get current prices
            futures_ticker = await asyncio.to_thread(exchange.get_futures_ticker, symbol)
            spot_ticker = await asyncio.to_thread(exchange.get_ticker, symbol)
            
            futures_price = futures_ticker['last']
            spot_price = spot_ticker['last']
            
            # Calculate basis (futures - spot)
            basis = futures_price - spot_price
            basis_percentage = (basis / spot_price) * 100
            
            # Annualized funding rate
            annual_funding = funding.annual_rate * 100  # As percentage
            
            self.logger.info(
                f"Funding analysis - Rate: {funding.rate:.4%}, "
                f"Annual: {annual_funding:.2f}%, Basis: {basis_percentage:.2f}%"
            )
            
            # Check for arbitrage opportunity
            signal = self._check_arbitrage_opportunity(
                funding, basis_percentage, annual_funding
            )
            
            return {
                'signal': signal,
                'funding_rate': funding.rate,
                'annual_funding': annual_funding,
                'basis_percentage': basis_percentage,
                'futures_price': futures_price,
                'spot_price': spot_price,
                'hours_until_funding': funding.hours_until_funding,
                'confidence': self._calculate_confidence(funding.rate, basis_percentage)
            }
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            return self._no_signal(str(e))
            
    def _check_arbitrage_opportunity(self, funding: FundingRate, 
                                   basis_pct: float, annual_funding: float) -> str:
        """Check if there's an arbitrage opportunity"""
        # High positive funding - shorts receive funding
        if funding.rate > self.funding_threshold:
            if basis_pct > 0.1:  # Futures premium exists
                return 'short_arbitrage'
                
        # High negative funding - longs receive funding  
        elif funding.rate < -self.funding_threshold:
            if basis_pct < -0.1:  # Futures discount exists
                return 'long_arbitrage'
                
        # Check if we should exit existing arbitrage
        if self.futures_position:
            if abs(funding.rate) < self.exit_threshold:
                return 'exit'
                
        return 'hold'
        
    async def execute_trade(self, exchange: BinanceFuturesClient, 
                          signal: Dict, capital: float) -> Optional[Dict]:
        """Execute funding arbitrage trade"""
        try:
            if signal['signal'] == 'short_arbitrage':
                return await self._execute_short_arbitrage(exchange, signal, capital)
                
            elif signal['signal'] == 'long_arbitrage':
                return await self._execute_long_arbitrage(exchange, signal, capital)
                
            elif signal['signal'] == 'exit':
                return await self._exit_arbitrage(exchange, signal)
                
            return None
            
        except Exception as e:
            self.logger.error(f"Trade execution failed: {e}")
            return None
            
    async def _execute_short_arbitrage(self, exchange: BinanceFuturesClient,
                                     signal: Dict, capital: float) -> Dict:
        """Execute short futures + long spot arbitrage"""
        symbol = self.symbol
        
        # Calculate position sizes
        position_capital = capital * self.max_position_size
        futures_size = position_capital / signal['futures_price']
        spot_size = (position_capital * self.hedge_ratio) / signal['spot_price']
        
        # Adjust for exchange minimums and precision
        futures_size = await self._adjust_position_size(
            exchange, symbol, futures_size, True
        )
        spot_size = await self._adjust_position_size(
            exchange, symbol, spot_size, False
        )
        
        results = []
        
        # 1. Short futures
        futures_order = await exchange.create_futures_order(
            symbol=symbol,
            order_type='market',
            side='sell',
            amount=futures_size,
            params={'leverage': self.leverage}
        )
        results.append(('futures_short', futures_order))
        self.futures_position = futures_order
        
        # 2. Buy spot (hedge)
        spot_order = await asyncio.to_thread(
            exchange.create_order,
            symbol=symbol,
            order_type='market', 
            side='buy',
            amount=spot_size
        )
        results.append(('spot_long', spot_order))
        self.spot_position = spot_order
        
        # Store entry funding rate
        self.entry_funding_rate = signal['funding_rate']
        
        self.logger.info(
            f"Opened short arbitrage - Futures: {futures_size}, "
            f"Spot: {spot_size}, Funding: {signal['funding_rate']:.4%}"
        )
        
        return {
            'strategy': 'funding_arbitrage',
            'type': 'short_arbitrage',
            'orders': results,
            'funding_rate': signal['funding_rate'],
            'expected_daily_return': signal['funding_rate'] * 3 * 100  # As percentage
        }
        
    async def _execute_long_arbitrage(self, exchange: BinanceFuturesClient,
                                    signal: Dict, capital: float) -> Dict:
        """Execute long futures arbitrage (negative funding)"""
        symbol = self.symbol
        
        # Calculate position size
        position_capital = capital * self.max_position_size
        futures_size = position_capital / signal['futures_price']
        
        # Adjust for exchange minimums
        futures_size = await self._adjust_position_size(
            exchange, symbol, futures_size, True
        )
        
        # Long futures to receive funding
        futures_order = await exchange.create_futures_order(
            symbol=symbol,
            order_type='market',
            side='buy',
            amount=futures_size,
            params={'leverage': self.leverage}
        )
        
        self.futures_position = futures_order
        self.entry_funding_rate = signal['funding_rate']
        
        self.logger.info(
            f"Opened long arbitrage - Size: {futures_size}, "
            f"Funding: {signal['funding_rate']:.4%}"
        )
        
        return {
            'strategy': 'funding_arbitrage',
            'type': 'long_arbitrage',
            'orders': [('futures_long', futures_order)],
            'funding_rate': signal['funding_rate'],
            'expected_daily_return': abs(signal['funding_rate']) * 3 * 100
        }
        
    async def _exit_arbitrage(self, exchange: BinanceFuturesClient,
                            signal: Dict) -> Dict:
        """Exit arbitrage positions"""
        results = []
        
        # Close futures position
        if self.futures_position:
            close_order = await exchange.close_futures_position(self.symbol)
            results.append(('close_futures', close_order))
            
        # Close spot position if exists
        if self.spot_position:
            # Get current spot balance
            balance = await asyncio.to_thread(exchange.get_balance)
            base_currency = self.symbol.split('/')[0]
            
            if base_currency in balance['free']:
                spot_amount = balance['free'][base_currency]
                if spot_amount > 0:
                    sell_order = await asyncio.to_thread(
                        exchange.create_order,
                        symbol=self.symbol,
                        order_type='market',
                        side='sell',
                        amount=spot_amount * 0.99  # Leave small buffer
                    )
                    results.append(('close_spot', sell_order))
                    
        # Reset positions
        self.futures_position = None
        self.spot_position = None
        self.entry_funding_rate = None
        
        self.logger.info("Closed arbitrage positions")
        
        return {
            'strategy': 'funding_arbitrage',
            'type': 'exit',
            'orders': results
        }
        
    async def _adjust_position_size(self, exchange: BinanceFuturesClient,
                                  symbol: str, size: float, 
                                  is_futures: bool) -> float:
        """Adjust position size for exchange requirements"""
        if is_futures:
            return await asyncio.to_thread(
                exchange.calculate_futures_position_size,
                symbol, size * exchange.get_futures_ticker(symbol)['last'],
                self.leverage, exchange.get_futures_ticker(symbol)['last']
            )
        else:
            return await asyncio.to_thread(
                exchange.calculate_position_size,
                symbol, size * exchange.get_ticker(symbol)['last'],
                exchange.get_ticker(symbol)['last']
            )
            
    def _calculate_confidence(self, funding_rate: float, basis_pct: float) -> float:
        """Calculate confidence score"""
        # Higher funding rate = higher confidence
        funding_score = min(abs(funding_rate) / 0.02, 1.0) * 0.5
        
        # Consistent basis = higher confidence
        basis_score = min(abs(basis_pct) / 1.0, 1.0) * 0.3
        
        # Time until funding (prefer closer to funding time)
        # This would need funding.hours_until_funding
        time_score = 0.2
        
        return funding_score + basis_score + time_score
        
    def _no_signal(self, reason: str) -> Dict:
        """Return no signal result"""
        return {
            'signal': 'hold',
            'reason': reason,
            'confidence': 0
        }
        
    def get_parameters(self) -> Dict:
        """Get strategy parameters"""
        return {
            'min_funding_rate': self.min_funding_rate,
            'funding_threshold': self.funding_threshold,
            'max_position_size': self.max_position_size,
            'hedge_ratio': self.hedge_ratio,
            'exit_threshold': self.exit_threshold,
            'leverage': self.leverage
        }