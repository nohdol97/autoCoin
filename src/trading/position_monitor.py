"""
Position monitor for tracking and managing open positions
"""

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import asyncio

from ..strategies.base import Position
from ..exchange.binance_client import BinanceClient
from ..logger import get_logger

logger = get_logger('position_monitor')


class PositionMonitor:
    """Monitors and manages trading positions"""
    
    def __init__(self, client: BinanceClient):
        self.client = client
        self.positions: Dict[str, Position] = {}  # symbol -> Position
        self.position_callbacks: List[Callable] = []
        self.is_monitoring = False
        self.monitor_interval = 5  # seconds
        
        # Performance tracking
        self.total_pnl = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.win_count = 0
        self.loss_count = 0
        
        logger.info("Initialized PositionMonitor")
        
    def add_position(self, position: Position):
        """Add a position to monitor"""
        self.positions[position.symbol] = position
        logger.info(f"Added position to monitor: {position.symbol} "
                   f"{position.side} {position.quantity} @ {position.entry_price}")
        
    def remove_position(self, symbol: str) -> Optional[Position]:
        """Remove a position from monitoring"""
        position = self.positions.pop(symbol, None)
        if position:
            logger.info(f"Removed position from monitor: {symbol}")
        return position
        
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get a specific position"""
        return self.positions.get(symbol)
        
    def get_all_positions(self) -> List[Position]:
        """Get all active positions"""
        return list(self.positions.values())
        
    def has_position(self, symbol: str) -> bool:
        """Check if position exists for symbol"""
        return symbol in self.positions
        
    def update_position_prices(self, symbol: str, current_price: float):
        """Update position with current price"""
        position = self.positions.get(symbol)
        if position:
            position.update_pnl(current_price)
            
            # Notify callbacks
            for callback in self.position_callbacks:
                try:
                    callback(position)
                except Exception as e:
                    logger.error(f"Error in position callback: {e}")
                    
    def check_exit_conditions(self, symbol: str, current_price: float) -> Optional[str]:
        """
        Check if position should be closed
        
        Returns:
            Exit reason (STOP_LOSS, TAKE_PROFIT) or None
        """
        position = self.positions.get(symbol)
        if not position:
            return None
            
        # Update P&L first
        position.update_pnl(current_price)
        
        # Check stop loss
        if position.should_stop_loss(current_price):
            logger.warning(f"Stop loss triggered for {symbol}: "
                          f"Price ${current_price:.2f} <= SL ${position.stop_loss:.2f}")
            return "STOP_LOSS"
            
        # Check take profit
        if position.should_take_profit(current_price):
            logger.info(f"Take profit triggered for {symbol}: "
                       f"Price ${current_price:.2f} >= TP ${position.take_profit:.2f}")
            return "TAKE_PROFIT"
            
        return None
        
    def close_position(self, symbol: str, exit_price: float) -> Optional[Position]:
        """Close a position and update statistics"""
        position = self.positions.get(symbol)
        if not position:
            return None
            
        # Close the position
        position.close(exit_price)
        
        # Update statistics
        self.realized_pnl += position.pnl
        if position.pnl > 0:
            self.win_count += 1
        elif position.pnl < 0:
            self.loss_count += 1
            
        # Remove from active positions
        self.remove_position(symbol)
        
        logger.info(f"Position closed: {symbol} "
                   f"PnL: ${position.pnl:.2f} ({position.pnl_percentage:.2f}%)")
        
        return position
        
    def calculate_total_exposure(self) -> float:
        """Calculate total position exposure in USDT"""
        total = 0.0
        for position in self.positions.values():
            # Assuming position value is quantity * current price
            # You might want to fetch current prices for accuracy
            total += position.quantity * position.entry_price
        return total
        
    def calculate_unrealized_pnl(self) -> float:
        """Calculate total unrealized P&L"""
        total = 0.0
        for position in self.positions.values():
            total += position.pnl
        self.unrealized_pnl = total
        return total
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get position monitor statistics"""
        total_trades = self.win_count + self.loss_count
        win_rate = (self.win_count / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'active_positions': len(self.positions),
            'total_exposure': self.calculate_total_exposure(),
            'unrealized_pnl': self.calculate_unrealized_pnl(),
            'realized_pnl': self.realized_pnl,
            'total_pnl': self.realized_pnl + self.unrealized_pnl,
            'total_trades': total_trades,
            'win_count': self.win_count,
            'loss_count': self.loss_count,
            'win_rate': win_rate
        }
        
    async def start_monitoring(self):
        """Start position monitoring loop"""
        self.is_monitoring = True
        logger.info("Starting position monitoring")
        
        while self.is_monitoring:
            try:
                # Update all positions with current prices
                for symbol, position in self.positions.items():
                    try:
                        ticker = self.client.get_ticker(symbol)
                        current_price = ticker.get('last', 0)
                        
                        if current_price > 0:
                            self.update_position_prices(symbol, current_price)
                            
                    except Exception as e:
                        logger.error(f"Error updating position {symbol}: {e}")
                        
                # Log statistics periodically
                stats = self.get_statistics()
                if stats['active_positions'] > 0:
                    logger.info(f"Position Monitor Stats: "
                               f"Active: {stats['active_positions']}, "
                               f"Unrealized PnL: ${stats['unrealized_pnl']:.2f}, "
                               f"Total PnL: ${stats['total_pnl']:.2f}")
                               
                await asyncio.sleep(self.monitor_interval)
                
            except Exception as e:
                logger.error(f"Error in position monitoring: {e}")
                await asyncio.sleep(self.monitor_interval)
                
    def stop_monitoring(self):
        """Stop position monitoring"""
        self.is_monitoring = False
        logger.info("Stopping position monitoring")
        
    def subscribe_position_update(self, callback: Callable[[Position], None]):
        """Subscribe to position updates"""
        self.position_callbacks.append(callback)
        logger.debug(f"Added position update callback: {callback.__name__}")
        
    def get_position_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all positions"""
        summary = []
        
        for position in self.positions.values():
            summary.append({
                'symbol': position.symbol,
                'side': position.side,
                'quantity': position.quantity,
                'entry_price': position.entry_price,
                'current_price': position.entry_price + (position.pnl / position.quantity),
                'pnl': position.pnl,
                'pnl_percentage': position.pnl_percentage,
                'stop_loss': position.stop_loss,
                'take_profit': position.take_profit,
                'duration': (datetime.now() - position.entry_time).total_seconds() / 3600  # hours
            })
            
        return summary
        
    def emergency_close_all(self) -> List[Position]:
        """Emergency close all positions (for safety)"""
        logger.warning("EMERGENCY: Closing all positions")
        
        closed_positions = []
        symbols = list(self.positions.keys())
        
        for symbol in symbols:
            try:
                ticker = self.client.get_ticker(symbol)
                current_price = ticker.get('last', 0)
                
                if current_price > 0:
                    position = self.close_position(symbol, current_price)
                    if position:
                        closed_positions.append(position)
                        
            except Exception as e:
                logger.error(f"Error closing position {symbol}: {e}")
                
        logger.info(f"Emergency closed {len(closed_positions)} positions")
        return closed_positions