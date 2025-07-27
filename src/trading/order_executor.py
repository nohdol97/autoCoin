"""
Order executor for placing and managing orders on Binance
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from ..exchange.binance_client import BinanceClient
from ..strategies.base import Position
from ..logger import get_logger

logger = get_logger('order_executor')


class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderSide(Enum):
    """Order sides"""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class Order:
    """Order representation"""
    
    def __init__(self, 
                 symbol: str,
                 side: OrderSide,
                 order_type: OrderType,
                 quantity: float,
                 price: Optional[float] = None,
                 stop_price: Optional[float] = None):
        self.symbol = symbol
        self.side = side
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.stop_price = stop_price
        self.order_id: Optional[str] = None
        self.status = OrderStatus.PENDING
        self.filled_quantity = 0.0
        self.average_price = 0.0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.exchange_order: Optional[Dict] = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'side': self.side.value,
            'order_type': self.order_type.value,
            'quantity': self.quantity,
            'price': self.price,
            'stop_price': self.stop_price,
            'order_id': self.order_id,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'average_price': self.average_price,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class OrderExecutor:
    """Executes trading orders on the exchange"""
    
    def __init__(self, client: BinanceClient):
        self.client = client
        self.orders: Dict[str, Order] = {}  # order_id -> Order
        self.position_orders: Dict[str, List[str]] = {}  # position_id -> [order_ids]
        
        logger.info("Initialized OrderExecutor")
        
    def create_market_order(self, 
                          symbol: str,
                          side: str,
                          quantity: float) -> Optional[Order]:
        """
        Create and execute a market order
        
        Args:
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Order quantity
            
        Returns:
            Executed order or None if failed
        """
        try:
            order_side = OrderSide.BUY if side == "BUY" else OrderSide.SELL
            order = Order(
                symbol=symbol,
                side=order_side,
                order_type=OrderType.MARKET,
                quantity=quantity
            )
            
            # Execute on exchange
            logger.info(f"Placing market {side} order: {quantity} {symbol}")
            
            exchange_order = self.client.create_order(
                symbol=symbol,
                order_type='market',
                side=side.lower(),
                amount=quantity
            )
            
            # Update order with exchange response
            order.order_id = str(exchange_order.get('id'))
            order.status = self._map_order_status(exchange_order.get('status'))
            order.filled_quantity = exchange_order.get('filled', 0)
            order.average_price = exchange_order.get('average', 0)
            order.exchange_order = exchange_order
            order.updated_at = datetime.now()
            
            # Store order
            self.orders[order.order_id] = order
            
            logger.info(f"Market order executed: {order.order_id} "
                       f"({order.filled_quantity} @ {order.average_price})")
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to create market order: {e}")
            return None
            
    def create_limit_order(self,
                         symbol: str,
                         side: str,
                         quantity: float,
                         price: float) -> Optional[Order]:
        """
        Create a limit order
        
        Args:
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Order quantity
            price: Limit price
            
        Returns:
            Created order or None if failed
        """
        try:
            order_side = OrderSide.BUY if side == "BUY" else OrderSide.SELL
            order = Order(
                symbol=symbol,
                side=order_side,
                order_type=OrderType.LIMIT,
                quantity=quantity,
                price=price
            )
            
            # Execute on exchange
            logger.info(f"Placing limit {side} order: {quantity} @ {price}")
            
            exchange_order = self.client.create_order(
                symbol=symbol,
                order_type='limit',
                side=side.lower(),
                amount=quantity,
                price=price
            )
            
            # Update order
            order.order_id = str(exchange_order.get('id'))
            order.status = self._map_order_status(exchange_order.get('status'))
            order.exchange_order = exchange_order
            order.updated_at = datetime.now()
            
            # Store order
            self.orders[order.order_id] = order
            
            logger.info(f"Limit order created: {order.order_id}")
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to create limit order: {e}")
            return None
            
    def create_stop_loss_order(self,
                             symbol: str,
                             quantity: float,
                             stop_price: float,
                             limit_price: Optional[float] = None) -> Optional[Order]:
        """
        Create a stop loss order
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            stop_price: Stop trigger price
            limit_price: Optional limit price (for stop-limit)
            
        Returns:
            Created order or None if failed
        """
        try:
            order = Order(
                symbol=symbol,
                side=OrderSide.SELL,
                order_type=OrderType.STOP_LOSS,
                quantity=quantity,
                stop_price=stop_price,
                price=limit_price
            )
            
            # Binance stop-loss implementation
            # Note: CCXT may not directly support stop orders for all exchanges
            # This is a simplified implementation
            logger.info(f"Creating stop loss order: {quantity} @ stop {stop_price}")
            
            # For now, we'll track it internally
            # In production, you'd use exchange-specific stop order API
            order.order_id = f"SL_{datetime.now().timestamp()}"
            order.status = OrderStatus.PENDING
            
            self.orders[order.order_id] = order
            
            logger.warning("Stop loss order created locally - manual monitoring required")
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to create stop loss order: {e}")
            return None
            
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        try:
            order = self.orders.get(order_id)
            if not order:
                logger.warning(f"Order not found: {order_id}")
                return False
                
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                logger.warning(f"Order {order_id} already {order.status.value}")
                return False
                
            # Cancel on exchange
            logger.info(f"Cancelling order: {order_id}")
            
            cancelled = self.client.cancel_order(order_id, order.symbol)
            
            if cancelled:
                order.status = OrderStatus.CANCELLED
                order.updated_at = datetime.now()
                logger.info(f"Order cancelled: {order_id}")
                return True
            else:
                logger.error(f"Failed to cancel order: {order_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
            
    def get_order_status(self, order_id: str) -> Optional[Order]:
        """
        Get order status
        
        Args:
            order_id: Order ID
            
        Returns:
            Updated order or None
        """
        try:
            order = self.orders.get(order_id)
            if not order:
                return None
                
            # Update from exchange
            exchange_order = self.client.get_order(order_id, order.symbol)
            
            if exchange_order:
                order.status = self._map_order_status(exchange_order.get('status'))
                order.filled_quantity = exchange_order.get('filled', 0)
                order.average_price = exchange_order.get('average', 0)
                order.exchange_order = exchange_order
                order.updated_at = datetime.now()
                
            return order
            
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return self.orders.get(order_id)
            
    def execute_position_entry(self, 
                             position: Position,
                             use_market_order: bool = True) -> Optional[Order]:
        """
        Execute position entry order
        
        Args:
            position: Position to enter
            use_market_order: Use market order (True) or limit order
            
        Returns:
            Entry order or None if failed
        """
        try:
            symbol = position.symbol
            side = "BUY" if position.side == "LONG" else "SELL"
            quantity = position.quantity
            
            if use_market_order:
                order = self.create_market_order(symbol, side, quantity)
            else:
                # Use current price as limit
                order = self.create_limit_order(
                    symbol, side, quantity, position.entry_price
                )
                
            if order:
                # Track position orders
                if position.symbol not in self.position_orders:
                    self.position_orders[position.symbol] = []
                self.position_orders[position.symbol].append(order.order_id)
                
                # Update position with actual entry price
                if order.status == OrderStatus.FILLED:
                    position.entry_price = order.average_price
                    
            return order
            
        except Exception as e:
            logger.error(f"Failed to execute position entry: {e}")
            return None
            
    def execute_position_exit(self,
                            position: Position,
                            use_market_order: bool = True) -> Optional[Order]:
        """
        Execute position exit order
        
        Args:
            position: Position to exit
            use_market_order: Use market order (True) or limit order
            
        Returns:
            Exit order or None if failed
        """
        try:
            symbol = position.symbol
            side = "SELL" if position.side == "LONG" else "BUY"
            quantity = position.quantity
            
            if use_market_order:
                order = self.create_market_order(symbol, side, quantity)
            else:
                # Use current price as limit
                current_price = self.client.get_ticker(symbol).get('last', 0)
                order = self.create_limit_order(
                    symbol, side, quantity, current_price
                )
                
            if order and position.symbol in self.position_orders:
                self.position_orders[position.symbol].append(order.order_id)
                
            return order
            
        except Exception as e:
            logger.error(f"Failed to execute position exit: {e}")
            return None
            
    def _map_order_status(self, exchange_status: str) -> OrderStatus:
        """Map exchange order status to internal status"""
        status_map = {
            'closed': OrderStatus.FILLED,
            'open': OrderStatus.PENDING,
            'canceled': OrderStatus.CANCELLED,
            'expired': OrderStatus.CANCELLED,
            'rejected': OrderStatus.REJECTED,
            'partially_filled': OrderStatus.PARTIALLY_FILLED
        }
        
        return status_map.get(exchange_status, OrderStatus.PENDING)
        
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders"""
        open_orders = []
        
        for order in self.orders.values():
            if order.status == OrderStatus.PENDING:
                if symbol is None or order.symbol == symbol:
                    open_orders.append(order)
                    
        return open_orders
        
    def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """Cancel all open orders"""
        cancelled_count = 0
        open_orders = self.get_open_orders(symbol)
        
        for order in open_orders:
            if self.cancel_order(order.order_id):
                cancelled_count += 1
                
        logger.info(f"Cancelled {cancelled_count} orders")
        return cancelled_count