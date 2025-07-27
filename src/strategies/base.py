"""
Base strategy class and interfaces
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import pandas as pd

from ..logger import get_logger

logger = get_logger('strategy_base')


class Signal(Enum):
    """Trading signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Position:
    """Position tracking"""
    def __init__(self, 
                 symbol: str,
                 side: str,
                 entry_price: float,
                 quantity: float,
                 strategy: str,
                 stop_loss: Optional[float] = None,
                 take_profit: Optional[float] = None):
        self.symbol = symbol
        self.side = side  # LONG or SHORT
        self.entry_price = entry_price
        self.quantity = quantity
        self.strategy = strategy
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.entry_time = datetime.now()
        self.exit_price = None
        self.exit_time = None
        self.pnl = 0.0
        self.pnl_percentage = 0.0
        
    def update_pnl(self, current_price: float):
        """Update P&L based on current price"""
        if self.side == "LONG":
            self.pnl = (current_price - self.entry_price) * self.quantity
            self.pnl_percentage = ((current_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            self.pnl = (self.entry_price - current_price) * self.quantity
            self.pnl_percentage = ((self.entry_price - current_price) / self.entry_price) * 100
            
    def should_stop_loss(self, current_price: float) -> bool:
        """Check if stop loss is hit"""
        if not self.stop_loss:
            return False
            
        if self.side == "LONG":
            return current_price <= self.stop_loss
        else:  # SHORT
            return current_price >= self.stop_loss
            
    def should_take_profit(self, current_price: float) -> bool:
        """Check if take profit is hit"""
        if not self.take_profit:
            return False
            
        if self.side == "LONG":
            return current_price >= self.take_profit
        else:  # SHORT
            return current_price <= self.take_profit
            
    def close(self, exit_price: float):
        """Close the position"""
        self.exit_price = exit_price
        self.exit_time = datetime.now()
        self.update_pnl(exit_price)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'quantity': self.quantity,
            'strategy': self.strategy,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'entry_time': self.entry_time.isoformat(),
            'exit_price': self.exit_price,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'pnl': self.pnl,
            'pnl_percentage': self.pnl_percentage,
            'current_price': self.exit_price or self.entry_price,
            'value': self.quantity * (self.exit_price or self.entry_price)
        }


class Strategy(ABC):
    """Base strategy class"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.position: Optional[Position] = None
        self.history: List[Position] = []
        
        # Risk management parameters
        self.stop_loss_pct = config.get('stop_loss', 2.0)
        self.take_profit_pct = config.get('take_profit', 5.0)
        self.max_position_size = config.get('max_position_size', 1.0)
        
        logger.info(f"Initialized {name} strategy with config: {config}")
        
    @abstractmethod
    def analyze(self, data: pd.DataFrame, current_price: float) -> Signal:
        """
        Analyze market data and generate trading signal
        
        Args:
            data: Historical OHLCV data
            current_price: Current market price
            
        Returns:
            Trading signal (BUY, SELL, or HOLD)
        """
        pass
        
    @abstractmethod
    def get_required_candles(self) -> int:
        """Get number of historical candles required for analysis"""
        pass
        
    def calculate_position_size(self, capital: float, current_price: float) -> float:
        """
        Calculate position size based on available capital
        
        Args:
            capital: Available capital in USDT
            current_price: Current BTC price
            
        Returns:
            Position size in BTC
        """
        # Use configured max position size (as percentage of capital)
        position_value = capital * self.max_position_size
        position_size = position_value / current_price
        
        return position_size
        
    def calculate_stop_loss(self, entry_price: float, side: str = "LONG") -> float:
        """Calculate stop loss price"""
        if side == "LONG":
            return entry_price * (1 - self.stop_loss_pct / 100)
        else:  # SHORT
            return entry_price * (1 + self.stop_loss_pct / 100)
            
    def calculate_take_profit(self, entry_price: float, side: str = "LONG") -> float:
        """Calculate take profit price"""
        if side == "LONG":
            return entry_price * (1 + self.take_profit_pct / 100)
        else:  # SHORT
            return entry_price * (1 - self.take_profit_pct / 100)
            
    def open_position(self, symbol: str, side: str, entry_price: float, 
                     quantity: float) -> Position:
        """Open a new position"""
        if self.position:
            raise ValueError("Position already exists")
            
        stop_loss = self.calculate_stop_loss(entry_price, side)
        take_profit = self.calculate_take_profit(entry_price, side)
        
        self.position = Position(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            strategy=self.name,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        logger.info(f"Opened {side} position: {quantity} @ ${entry_price:.2f}, "
                   f"SL: ${stop_loss:.2f}, TP: ${take_profit:.2f}")
        
        return self.position
        
    def close_position(self, exit_price: float) -> Position:
        """Close current position"""
        if not self.position:
            raise ValueError("No position to close")
            
        self.position.close(exit_price)
        self.history.append(self.position)
        
        logger.info(f"Closed position: PnL ${self.position.pnl:.2f} "
                   f"({self.position.pnl_percentage:.2f}%)")
        
        closed_position = self.position
        self.position = None
        
        return closed_position
        
    def check_exit_conditions(self, current_price: float) -> Optional[str]:
        """Check if position should be closed"""
        if not self.position:
            return None
            
        if self.position.should_stop_loss(current_price):
            return "STOP_LOSS"
        elif self.position.should_take_profit(current_price):
            return "TAKE_PROFIT"
            
        return None
        
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get strategy performance statistics"""
        if not self.history:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_pnl': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0
            }
            
        winning_trades = [p for p in self.history if p.pnl > 0]
        losing_trades = [p for p in self.history if p.pnl < 0]
        
        total_pnl = sum(p.pnl for p in self.history)
        pnls = [p.pnl for p in self.history]
        
        return {
            'total_trades': len(self.history),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(self.history) * 100,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / len(self.history),
            'best_trade': max(pnls) if pnls else 0.0,
            'worst_trade': min(pnls) if pnls else 0.0
        }
        
    def reset(self):
        """Reset strategy state"""
        if self.position:
            logger.warning(f"Resetting strategy with open position")
        self.position = None
        self.history.clear()
        logger.info(f"Strategy {self.name} reset")