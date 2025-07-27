"""
Futures Position Manager
Handles position tracking, risk management, and order execution for futures
"""
import asyncio
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import json

from ..exchange.binance_futures_client import BinanceFuturesClient
from ..utils.risk_manager import RiskManager
from .futures_types import (
    FuturesPosition, FuturesOrder, FundingRate, RiskMetrics,
    PositionSide, MarginMode, OrderType
)


class FuturesPositionManager:
    """Manages futures positions and risk"""
    
    def __init__(self, exchange: BinanceFuturesClient, risk_manager: RiskManager):
        self.exchange = exchange
        self.risk_manager = risk_manager
        self.logger = logging.getLogger(__name__)
        self.positions: Dict[str, FuturesPosition] = {}
        self.orders: Dict[str, FuturesOrder] = {}
        self._position_update_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize position manager"""
        await self.update_positions()
        self.logger.info("Futures position manager initialized")
        
    async def update_positions(self):
        """Update all positions from exchange"""
        async with self._position_update_lock:
            try:
                raw_positions = await asyncio.to_thread(self.exchange.get_futures_positions)
                
                self.positions.clear()
                for pos in raw_positions:
                    if pos['contracts'] != 0:  # Only active positions
                        position = self._parse_position(pos)
                        self.positions[position.symbol] = position
                        
                self.logger.debug(f"Updated {len(self.positions)} futures positions")
                
            except Exception as e:
                self.logger.error(f"Failed to update positions: {e}")
                
    def _parse_position(self, raw_position: Dict) -> FuturesPosition:
        """Parse raw position data into FuturesPosition"""
        side = PositionSide.LONG if raw_position['side'] == 'long' else PositionSide.SHORT
        margin_mode = MarginMode.ISOLATED if raw_position.get('marginMode') == 'isolated' else MarginMode.CROSS
        
        return FuturesPosition(
            symbol=raw_position['symbol'],
            side=side,
            contracts=raw_position['contracts'],
            entry_price=raw_position['entryPrice'] or 0,
            mark_price=raw_position['markPrice'] or 0,
            liquidation_price=raw_position.get('liquidationPrice'),
            unrealized_pnl=raw_position['unrealizedPnl'] or 0,
            realized_pnl=raw_position.get('realizedPnl', 0),
            margin=raw_position.get('initialMargin', 0),
            leverage=raw_position.get('leverage', 1),
            margin_mode=margin_mode,
            timestamp=datetime.now()
        )
        
    async def open_position(self, symbol: str, side: str, size: float, 
                          leverage: int = 1, margin_mode: str = 'isolated',
                          stop_loss: Optional[float] = None,
                          take_profit: Optional[float] = None) -> Dict:
        """Open a new futures position"""
        try:
            # Check if position already exists
            if symbol in self.positions:
                self.logger.warning(f"Position already exists for {symbol}")
                return {'status': 'error', 'message': 'Position already exists'}
                
            # Set leverage and margin mode
            await asyncio.to_thread(self.exchange.set_leverage, symbol, leverage)
            await asyncio.to_thread(self.exchange.set_margin_mode, symbol, margin_mode)
            
            # Create order
            order = await asyncio.to_thread(
                self.exchange.create_futures_order,
                symbol=symbol,
                order_type='market',
                side=side,
                amount=size,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            # Update positions
            await self.update_positions()
            
            self.logger.info(f"Opened {side} position for {size} {symbol} at {leverage}x")
            return order
            
        except Exception as e:
            self.logger.error(f"Failed to open position: {e}")
            return {'status': 'error', 'message': str(e)}
            
    async def close_position(self, symbol: str, percentage: float = 100) -> Dict:
        """Close a futures position (partially or fully)"""
        try:
            position = self.positions.get(symbol)
            if not position:
                return {'status': 'error', 'message': 'No position found'}
                
            # Calculate close size
            close_size = abs(position.contracts) * (percentage / 100)
            close_side = 'sell' if position.side == PositionSide.LONG else 'buy'
            
            # Create close order
            order = await asyncio.to_thread(
                self.exchange.create_futures_order,
                symbol=symbol,
                order_type='market',
                side=close_side,
                amount=close_size
            )
            
            # Update positions
            await self.update_positions()
            
            self.logger.info(f"Closed {percentage}% of {symbol} position")
            return order
            
        except Exception as e:
            self.logger.error(f"Failed to close position: {e}")
            return {'status': 'error', 'message': str(e)}
            
    async def adjust_leverage(self, symbol: str, new_leverage: int) -> Dict:
        """Adjust leverage for a position"""
        try:
            # Check max leverage
            max_leverage = await asyncio.to_thread(self.exchange.get_max_leverage, symbol)
            if new_leverage > max_leverage:
                return {'status': 'error', 'message': f'Leverage exceeds maximum ({max_leverage}x)'}
                
            result = await asyncio.to_thread(self.exchange.set_leverage, symbol, new_leverage)
            
            # Update position info
            await self.update_positions()
            
            self.logger.info(f"Adjusted leverage for {symbol} to {new_leverage}x")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to adjust leverage: {e}")
            return {'status': 'error', 'message': str(e)}
            
    async def add_stop_loss(self, symbol: str, stop_price: float) -> Dict:
        """Add or update stop loss for a position"""
        try:
            position = self.positions.get(symbol)
            if not position:
                return {'status': 'error', 'message': 'No position found'}
                
            side = 'sell' if position.side == PositionSide.LONG else 'buy'
            
            order = await asyncio.to_thread(
                self.exchange.futures_exchange.create_order,
                symbol=symbol,
                type='stop_market',
                side=side,
                amount=abs(position.contracts),
                stopPrice=stop_price,
                params={'stopPrice': stop_price, 'workingType': 'MARK_PRICE'}
            )
            
            self.logger.info(f"Added stop loss at {stop_price} for {symbol}")
            return order
            
        except Exception as e:
            self.logger.error(f"Failed to add stop loss: {e}")
            return {'status': 'error', 'message': str(e)}
            
    async def add_take_profit(self, symbol: str, take_profit_price: float) -> Dict:
        """Add or update take profit for a position"""
        try:
            position = self.positions.get(symbol)
            if not position:
                return {'status': 'error', 'message': 'No position found'}
                
            side = 'sell' if position.side == PositionSide.LONG else 'buy'
            
            order = await asyncio.to_thread(
                self.exchange.futures_exchange.create_order,
                symbol=symbol,
                type='take_profit_market',
                side=side,
                amount=abs(position.contracts),
                stopPrice=take_profit_price,
                params={'stopPrice': take_profit_price, 'workingType': 'MARK_PRICE'}
            )
            
            self.logger.info(f"Added take profit at {take_profit_price} for {symbol}")
            return order
            
        except Exception as e:
            self.logger.error(f"Failed to add take profit: {e}")
            return {'status': 'error', 'message': str(e)}
            
    async def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        """Get current funding rate for a symbol"""
        try:
            funding_data = await asyncio.to_thread(self.exchange.get_funding_rate, symbol)
            
            return FundingRate(
                symbol=symbol,
                rate=funding_data['fundingRate'],
                timestamp=datetime.fromtimestamp(funding_data['timestamp'] / 1000),
                next_funding_time=datetime.fromtimestamp(funding_data['fundingDatetime'] / 1000)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get funding rate: {e}")
            return None
            
    async def get_risk_metrics(self) -> RiskMetrics:
        """Calculate current risk metrics"""
        try:
            # Get account info
            balance = await asyncio.to_thread(self.exchange.get_futures_balance)
            
            # Calculate metrics
            total_margin = balance['USDT']['total']
            free_margin = balance['USDT']['free']
            used_margin = balance['USDT']['used']
            
            # Calculate leverage and notional
            total_notional = 0
            max_leverage = 0
            
            for position in self.positions.values():
                total_notional += position.notional
                max_leverage = max(max_leverage, position.leverage)
                
            current_leverage = total_notional / total_margin if total_margin > 0 else 0
            margin_level = (total_margin / used_margin * 100) if used_margin > 0 else float('inf')
            
            # Get PnL data (simplified for now)
            daily_pnl = sum(p.unrealized_pnl for p in self.positions.values())
            weekly_pnl = daily_pnl  # Would need historical data for accurate weekly
            
            return RiskMetrics(
                max_leverage=max_leverage,
                current_leverage=int(current_leverage),
                total_margin=total_margin,
                free_margin=free_margin,
                margin_level=margin_level,
                positions_count=len(self.positions),
                total_notional=total_notional,
                max_position_size=total_margin * 0.1,  # 10% per position
                daily_pnl=daily_pnl,
                weekly_pnl=weekly_pnl
            )
            
        except Exception as e:
            self.logger.error(f"Failed to calculate risk metrics: {e}")
            # Return safe defaults
            return RiskMetrics(
                max_leverage=1,
                current_leverage=1,
                total_margin=0,
                free_margin=0,
                margin_level=100,
                positions_count=0,
                total_notional=0,
                max_position_size=0,
                daily_pnl=0,
                weekly_pnl=0
            )
            
    async def check_liquidation_risk(self) -> List[Dict]:
        """Check positions at risk of liquidation"""
        at_risk = []
        
        for symbol, position in self.positions.items():
            if not position.liquidation_price:
                continue
                
            mark_price = position.mark_price
            liq_price = position.liquidation_price
            
            # Calculate distance to liquidation
            if position.side == PositionSide.LONG:
                distance_pct = ((mark_price - liq_price) / mark_price) * 100
            else:
                distance_pct = ((liq_price - mark_price) / mark_price) * 100
                
            # Warn if within 10% of liquidation
            if distance_pct < 10:
                at_risk.append({
                    'symbol': symbol,
                    'side': position.side.value,
                    'mark_price': mark_price,
                    'liquidation_price': liq_price,
                    'distance_percentage': distance_pct,
                    'risk_level': 'HIGH' if distance_pct < 5 else 'MEDIUM'
                })
                
        return at_risk
        
    async def emergency_close_all(self) -> List[Dict]:
        """Emergency close all positions"""
        results = []
        
        for symbol in list(self.positions.keys()):
            try:
                result = await self.close_position(symbol)
                results.append({
                    'symbol': symbol,
                    'status': 'closed',
                    'order': result
                })
            except Exception as e:
                results.append({
                    'symbol': symbol,
                    'status': 'error',
                    'error': str(e)
                })
                
        self.logger.warning(f"Emergency closed {len(results)} positions")
        return results
        
    def get_position_summary(self) -> Dict:
        """Get summary of all positions"""
        if not self.positions:
            return {
                'count': 0,
                'total_notional': 0,
                'total_pnl': 0,
                'positions': []
            }
            
        total_notional = sum(p.notional for p in self.positions.values())
        total_pnl = sum(p.unrealized_pnl for p in self.positions.values())
        
        return {
            'count': len(self.positions),
            'total_notional': total_notional,
            'total_pnl': total_pnl,
            'total_pnl_percentage': (total_pnl / total_notional * 100) if total_notional > 0 else 0,
            'positions': [p.to_dict() for p in self.positions.values()]
        }