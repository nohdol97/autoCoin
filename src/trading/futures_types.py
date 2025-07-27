"""
Futures Trading Types and Data Classes
"""
from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum


class PositionSide(Enum):
    """Position side for futures"""
    LONG = "long"
    SHORT = "short"
    BOTH = "both"  # For hedge mode


class MarginMode(Enum):
    """Margin mode for futures"""
    ISOLATED = "isolated"
    CROSS = "cross"


class OrderType(Enum):
    """Futures order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    TAKE_PROFIT_MARKET = "take_profit_market"
    STOP_LIMIT = "stop_limit"
    TAKE_PROFIT_LIMIT = "take_profit_limit"


@dataclass
class FuturesPosition:
    """Futures position data"""
    symbol: str
    side: PositionSide
    contracts: float
    entry_price: float
    mark_price: float
    liquidation_price: Optional[float]
    unrealized_pnl: float
    realized_pnl: float
    margin: float
    leverage: int
    margin_mode: MarginMode
    timestamp: datetime
    
    @property
    def notional(self) -> float:
        """Calculate notional value"""
        return abs(self.contracts) * self.mark_price
        
    @property
    def pnl_percentage(self) -> float:
        """Calculate PnL percentage"""
        if self.margin == 0:
            return 0
        return (self.unrealized_pnl / self.margin) * 100
        
    @property
    def margin_ratio(self) -> float:
        """Calculate margin ratio"""
        if self.notional == 0:
            return 0
        return (self.margin / self.notional) * 100
        
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'side': self.side.value,
            'contracts': self.contracts,
            'entry_price': self.entry_price,
            'mark_price': self.mark_price,
            'liquidation_price': self.liquidation_price,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'margin': self.margin,
            'leverage': self.leverage,
            'margin_mode': self.margin_mode.value,
            'notional': self.notional,
            'pnl_percentage': self.pnl_percentage,
            'margin_ratio': self.margin_ratio,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class FuturesOrder:
    """Futures order data"""
    order_id: str
    symbol: str
    type: OrderType
    side: str  # buy/sell
    quantity: float
    price: Optional[float]
    stop_price: Optional[float]
    status: str
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'type': self.type.value,
            'side': self.side,
            'quantity': self.quantity,
            'price': self.price,
            'stop_price': self.stop_price,
            'status': self.status,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class FundingRate:
    """Funding rate data"""
    symbol: str
    rate: float
    timestamp: datetime
    next_funding_time: datetime
    
    @property
    def annual_rate(self) -> float:
        """Calculate annualized funding rate"""
        # Funding is typically every 8 hours, so 3 times per day
        return self.rate * 3 * 365
        
    @property
    def hours_until_funding(self) -> float:
        """Calculate hours until next funding"""
        delta = self.next_funding_time - datetime.now()
        return delta.total_seconds() / 3600
        
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'rate': self.rate,
            'annual_rate': self.annual_rate,
            'timestamp': self.timestamp.isoformat(),
            'next_funding_time': self.next_funding_time.isoformat(),
            'hours_until_funding': self.hours_until_funding
        }


@dataclass
class RiskMetrics:
    """Risk metrics for futures trading"""
    max_leverage: int
    current_leverage: int
    total_margin: float
    free_margin: float
    margin_level: float  # (equity / used margin) * 100
    positions_count: int
    total_notional: float
    max_position_size: float
    daily_pnl: float
    weekly_pnl: float
    
    @property
    def margin_usage_percentage(self) -> float:
        """Calculate margin usage percentage"""
        if self.total_margin == 0:
            return 0
        return ((self.total_margin - self.free_margin) / self.total_margin) * 100
        
    @property
    def is_overleveraged(self) -> bool:
        """Check if account is overleveraged"""
        return self.margin_level < 150  # Below 150% is risky
        
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'max_leverage': self.max_leverage,
            'current_leverage': self.current_leverage,
            'total_margin': self.total_margin,
            'free_margin': self.free_margin,
            'margin_level': self.margin_level,
            'margin_usage_percentage': self.margin_usage_percentage,
            'positions_count': self.positions_count,
            'total_notional': self.total_notional,
            'max_position_size': self.max_position_size,
            'daily_pnl': self.daily_pnl,
            'weekly_pnl': self.weekly_pnl,
            'is_overleveraged': self.is_overleveraged
        }