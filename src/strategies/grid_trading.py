"""
Grid Trading Strategy for Futures
Places buy and sell orders at regular intervals to profit from market volatility
"""
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from decimal import Decimal

from .base_strategy import BaseStrategy
from ..exchange.binance_futures_client import BinanceFuturesClient


class GridTradingStrategy(BaseStrategy):
    """
    Grid Trading Strategy
    
    Creates a grid of buy/sell orders at fixed intervals
    Profits from market volatility within a range
    """
    
    def __init__(self, config: Dict):
        super().__init__(config)
        
        # Grid parameters
        self.grid_levels = config.get('grid_levels', 10)  # Number of grid levels
        self.grid_spacing = config.get('grid_spacing', 0.002)  # 0.2% between levels
        self.grid_size_pct = config.get('grid_size_pct', 0.1)  # 10% of capital per grid
        self.leverage = config.get('leverage', 3)
        
        # Range parameters
        self.use_dynamic_range = config.get('use_dynamic_range', True)
        self.range_period = config.get('range_period', 24)  # Hours for range calculation
        self.range_multiplier = config.get('range_multiplier', 1.5)
        
        # Risk parameters
        self.max_position_size = config.get('max_position_size', 0.5)  # 50% of capital
        self.stop_loss_pct = config.get('stop_loss_pct', 0.05)  # 5% stop loss
        
        # Grid state
        self.grid_orders: Dict[float, Dict] = {}  # price -> order
        self.grid_center = None
        self.grid_upper = None
        self.grid_lower = None
        self.last_update = None
        
    async def analyze(self, exchange: BinanceFuturesClient, symbol: str) -> Dict:
        """Analyze market for grid trading opportunity"""
        try:
            # Get current price
            ticker = await asyncio.to_thread(exchange.get_futures_ticker, symbol)
            current_price = ticker['last']
            
            # Get historical data for range calculation
            ohlcv = await asyncio.to_thread(
                exchange.get_futures_ohlcv,
                symbol, '1h', limit=self.range_period
            )
            
            # Calculate trading range
            if self.use_dynamic_range:
                range_data = self._calculate_dynamic_range(ohlcv, current_price)
            else:
                range_data = self._calculate_fixed_range(current_price)
                
            # Check if grid needs update
            needs_update = self._check_grid_update_needed(
                current_price, range_data, ohlcv
            )
            
            # Calculate grid efficiency
            efficiency = self._calculate_grid_efficiency(ohlcv, range_data)
            
            signal = 'create_grid' if needs_update else 'maintain_grid'
            
            return {
                'signal': signal,
                'current_price': current_price,
                'grid_center': range_data['center'],
                'grid_upper': range_data['upper'],
                'grid_lower': range_data['lower'],
                'grid_levels': self._calculate_grid_levels(range_data),
                'volatility': range_data.get('volatility', 0),
                'efficiency_score': efficiency,
                'confidence': self._calculate_confidence(efficiency, range_data)
            }
            
        except Exception as e:
            self.logger.error(f"Grid analysis failed: {e}")
            return self._no_signal(str(e))
            
    def _calculate_dynamic_range(self, ohlcv: pd.DataFrame, current_price: float) -> Dict:
        """Calculate dynamic price range based on recent volatility"""
        # Calculate ATR for volatility
        high = ohlcv['high']
        low = ohlcv['low']
        close = ohlcv['close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR
        atr = tr.rolling(14).mean().iloc[-1]
        volatility = atr / current_price
        
        # Calculate range
        range_size = atr * self.range_multiplier
        
        # Use recent price action for center
        recent_high = high.tail(self.range_period // 4).max()
        recent_low = low.tail(self.range_period // 4).min()
        center = (recent_high + recent_low) / 2
        
        return {
            'center': center,
            'upper': center + range_size,
            'lower': center - range_size,
            'volatility': volatility,
            'atr': atr
        }
        
    def _calculate_fixed_range(self, current_price: float) -> Dict:
        """Calculate fixed price range"""
        range_size = current_price * self.grid_spacing * self.grid_levels / 2
        
        return {
            'center': current_price,
            'upper': current_price + range_size,
            'lower': current_price - range_size,
            'volatility': 0
        }
        
    def _calculate_grid_levels(self, range_data: Dict) -> List[float]:
        """Calculate grid price levels"""
        levels = []
        center = range_data['center']
        
        # Calculate levels above and below center
        for i in range(self.grid_levels // 2):
            # Above center
            level_up = center * (1 + self.grid_spacing * (i + 1))
            if level_up <= range_data['upper']:
                levels.append(level_up)
                
            # Below center  
            level_down = center * (1 - self.grid_spacing * (i + 1))
            if level_down >= range_data['lower']:
                levels.append(level_down)
                
        levels.sort()
        return levels
        
    def _check_grid_update_needed(self, current_price: float, 
                                range_data: Dict, ohlcv: pd.DataFrame) -> bool:
        """Check if grid needs to be updated"""
        # First time setup
        if not self.grid_center:
            return True
            
        # Check if price moved out of range
        if current_price > self.grid_upper * 1.02 or current_price < self.grid_lower * 0.98:
            self.logger.info("Price moved out of grid range")
            return True
            
        # Check if it's been too long since last update
        if self.last_update:
            hours_since_update = (datetime.now() - self.last_update).total_seconds() / 3600
            if hours_since_update > 24:
                self.logger.info("Grid update due to time")
                return True
                
        # Check if volatility changed significantly
        if 'volatility' in range_data:
            old_range = self.grid_upper - self.grid_lower
            new_range = range_data['upper'] - range_data['lower']
            if abs(new_range - old_range) / old_range > 0.2:
                self.logger.info("Grid update due to volatility change")
                return True
                
        return False
        
    def _calculate_grid_efficiency(self, ohlcv: pd.DataFrame, range_data: Dict) -> float:
        """Calculate how efficient the grid would be based on price movements"""
        # Count how many times price would cross grid levels
        prices = ohlcv['close'].values
        levels = self._calculate_grid_levels(range_data)
        
        if len(levels) < 2:
            return 0
            
        crossings = 0
        for i in range(1, len(prices)):
            for level in levels:
                if (prices[i-1] <= level <= prices[i]) or (prices[i] <= level <= prices[i-1]):
                    crossings += 1
                    
        # Normalize by time and levels
        efficiency = crossings / (len(prices) * len(levels))
        return min(efficiency * 10, 1.0)  # Scale to 0-1
        
    async def execute_trade(self, exchange: BinanceFuturesClient,
                          signal: Dict, capital: float) -> Optional[Dict]:
        """Execute grid trading setup or maintenance"""
        try:
            if signal['signal'] == 'create_grid':
                return await self._create_grid(exchange, signal, capital)
            elif signal['signal'] == 'maintain_grid':
                return await self._maintain_grid(exchange, signal)
                
            return None
            
        except Exception as e:
            self.logger.error(f"Grid execution failed: {e}")
            return None
            
    async def _create_grid(self, exchange: BinanceFuturesClient,
                         signal: Dict, capital: float) -> Dict:
        """Create new grid"""
        # Cancel existing grid orders
        await self._cancel_all_grid_orders(exchange)
        
        # Update grid parameters
        self.grid_center = signal['grid_center']
        self.grid_upper = signal['grid_upper']
        self.grid_lower = signal['grid_lower']
        self.last_update = datetime.now()
        
        # Calculate order size
        grid_capital = capital * self.max_position_size
        order_capital = grid_capital / self.grid_levels
        
        current_price = signal['current_price']
        orders_created = []
        
        # Set leverage
        await asyncio.to_thread(
            exchange.set_leverage, self.symbol, self.leverage
        )
        
        # Create grid orders
        for level in signal['grid_levels']:
            try:
                # Determine order side
                if level > current_price:
                    # Sell order above current price
                    side = 'sell'
                    order_type = 'limit'
                else:
                    # Buy order below current price
                    side = 'buy'
                    order_type = 'limit'
                    
                # Calculate order size
                order_size = await asyncio.to_thread(
                    exchange.calculate_futures_position_size,
                    self.symbol, order_capital, self.leverage, level
                )
                
                # Create order
                order = await asyncio.to_thread(
                    exchange.create_futures_order,
                    symbol=self.symbol,
                    order_type=order_type,
                    side=side,
                    amount=order_size,
                    price=level
                )
                
                self.grid_orders[level] = order
                orders_created.append({
                    'level': level,
                    'side': side,
                    'size': order_size,
                    'order_id': order['id']
                })
                
            except Exception as e:
                self.logger.error(f"Failed to create grid order at {level}: {e}")
                
        self.logger.info(
            f"Created grid with {len(orders_created)} orders "
            f"between {self.grid_lower:.2f} and {self.grid_upper:.2f}"
        )
        
        return {
            'strategy': 'grid_trading',
            'type': 'create_grid',
            'orders_created': len(orders_created),
            'grid_range': [self.grid_lower, self.grid_upper],
            'orders': orders_created
        }
        
    async def _maintain_grid(self, exchange: BinanceFuturesClient,
                           signal: Dict) -> Dict:
        """Maintain existing grid by replacing filled orders"""
        filled_orders = []
        new_orders = []
        
        # Check each grid order
        for price, order in list(self.grid_orders.items()):
            try:
                # Check order status
                order_status = await asyncio.to_thread(
                    exchange.futures_exchange.fetch_order,
                    order['id'], self.symbol
                )
                
                if order_status['status'] == 'closed':
                    # Order filled, create opposite order
                    filled_orders.append(price)
                    
                    # Determine new order parameters
                    if order['side'] == 'buy':
                        # Was buy, create sell above
                        new_price = price * (1 + self.grid_spacing)
                        new_side = 'sell'
                    else:
                        # Was sell, create buy below
                        new_price = price * (1 - self.grid_spacing)
                        new_side = 'buy'
                        
                    # Check if new price is within range
                    if self.grid_lower <= new_price <= self.grid_upper:
                        # Create new order
                        new_order = await asyncio.to_thread(
                            exchange.create_futures_order,
                            symbol=self.symbol,
                            order_type='limit',
                            side=new_side,
                            amount=order['amount'],
                            price=new_price
                        )
                        
                        self.grid_orders[new_price] = new_order
                        new_orders.append({
                            'price': new_price,
                            'side': new_side,
                            'size': order['amount']
                        })
                        
                    # Remove filled order
                    del self.grid_orders[price]
                    
            except Exception as e:
                self.logger.error(f"Error checking order at {price}: {e}")
                
        if filled_orders:
            self.logger.info(
                f"Grid maintenance: {len(filled_orders)} orders filled, "
                f"{len(new_orders)} new orders created"
            )
            
        return {
            'strategy': 'grid_trading',
            'type': 'maintain_grid',
            'filled_orders': len(filled_orders),
            'new_orders': len(new_orders),
            'active_orders': len(self.grid_orders)
        }
        
    async def _cancel_all_grid_orders(self, exchange: BinanceFuturesClient):
        """Cancel all grid orders"""
        for price, order in list(self.grid_orders.items()):
            try:
                await asyncio.to_thread(
                    exchange.futures_exchange.cancel_order,
                    order['id'], self.symbol
                )
            except Exception as e:
                self.logger.error(f"Failed to cancel order at {price}: {e}")
                
        self.grid_orders.clear()
        
    def _calculate_confidence(self, efficiency: float, range_data: Dict) -> float:
        """Calculate confidence score"""
        # Efficiency score (most important)
        efficiency_score = efficiency * 0.5
        
        # Volatility score (prefer medium volatility)
        volatility = range_data.get('volatility', 0)
        if 0.01 < volatility < 0.05:  # 1-5% volatility
            volatility_score = 0.3
        elif 0.005 < volatility < 0.08:  # 0.5-8% volatility  
            volatility_score = 0.2
        else:
            volatility_score = 0.1
            
        # Range validity
        range_score = 0.2
        
        return efficiency_score + volatility_score + range_score
        
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
            'grid_levels': self.grid_levels,
            'grid_spacing': self.grid_spacing,
            'grid_size_pct': self.grid_size_pct,
            'leverage': self.leverage,
            'use_dynamic_range': self.use_dynamic_range,
            'range_period': self.range_period,
            'range_multiplier': self.range_multiplier,
            'max_position_size': self.max_position_size
        }