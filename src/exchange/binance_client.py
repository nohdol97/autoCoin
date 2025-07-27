import ccxt
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
import pandas as pd

class BinanceClient:
    """Binance API client wrapper for AutoCoin trading bot"""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.logger = logging.getLogger(__name__)
        self.testnet = testnet
        
        # Initialize exchange
        if testnet:
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',  # Changed from 'future' to 'spot' for testnet
                    'test': True,
                }
            })
            # Set testnet URLs
            self.exchange.urls['api'] = {
                'public': 'https://testnet.binance.vision/api/v3',
                'private': 'https://testnet.binance.vision/api/v3',
            }
            self.logger.info("Initialized Binance client in TESTNET mode")
        else:
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
            })
            self.logger.info("Initialized Binance client in LIVE mode")
            
    def get_balance(self) -> Dict:
        """Get account balance"""
        try:
            balance = self.exchange.fetch_balance()
            self.logger.debug(f"Fetched balance: {balance['total']}")
            return balance
        except Exception as e:
            self.logger.error(f"Failed to fetch balance: {e}")
            raise
            
    def get_ticker(self, symbol: str) -> Dict:
        """Get current ticker information"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            self.logger.debug(f"Fetched ticker for {symbol}: {ticker['last']}")
            return ticker
        except Exception as e:
            self.logger.error(f"Failed to fetch ticker for {symbol}: {e}")
            raise
            
    def get_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> pd.DataFrame:
        """Get OHLCV data"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            self.logger.debug(f"Fetched {len(df)} candles for {symbol}")
            return df
        except Exception as e:
            self.logger.error(f"Failed to fetch OHLCV for {symbol}: {e}")
            raise
            
    def create_order(self, symbol: str, order_type: str, side: str, amount: float, 
                    price: Optional[float] = None, params: Dict = None) -> Dict:
        """Create an order"""
        try:
            if params is None:
                params = {}
                
            order = self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
                params=params
            )
            self.logger.info(f"Created {side} order for {amount} {symbol} at {price or 'market'}")
            return order
        except Exception as e:
            self.logger.error(f"Failed to create order: {e}")
            raise
            
    def cancel_order(self, order_id: str, symbol: str) -> Dict:
        """Cancel an order"""
        try:
            result = self.exchange.cancel_order(order_id, symbol)
            self.logger.info(f"Cancelled order {order_id}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to cancel order {order_id}: {e}")
            raise
            
    def get_order(self, order_id: str, symbol: str) -> Dict:
        """Get order information"""
        try:
            order = self.exchange.fetch_order(order_id, symbol)
            return order
        except Exception as e:
            self.logger.error(f"Failed to fetch order {order_id}: {e}")
            raise
            
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get all open orders"""
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            self.logger.debug(f"Found {len(orders)} open orders")
            return orders
        except Exception as e:
            self.logger.error(f"Failed to fetch open orders: {e}")
            raise
            
    def get_order_book(self, symbol: str, limit: int = 10) -> Dict:
        """Get order book"""
        try:
            order_book = self.exchange.fetch_order_book(symbol, limit)
            return order_book
        except Exception as e:
            self.logger.error(f"Failed to fetch order book for {symbol}: {e}")
            raise
            
    def get_trades(self, symbol: str, limit: int = 50) -> List[Dict]:
        """Get recent trades"""
        try:
            trades = self.exchange.fetch_trades(symbol, limit=limit)
            return trades
        except Exception as e:
            self.logger.error(f"Failed to fetch trades for {symbol}: {e}")
            raise
            
    def get_my_trades(self, symbol: str, limit: int = 50) -> List[Dict]:
        """Get my trades"""
        try:
            trades = self.exchange.fetch_my_trades(symbol, limit=limit)
            self.logger.debug(f"Found {len(trades)} trades for {symbol}")
            return trades
        except Exception as e:
            self.logger.error(f"Failed to fetch my trades for {symbol}: {e}")
            raise
            
    def get_exchange_info(self) -> Dict:
        """Get exchange information"""
        try:
            return self.exchange.load_markets()
        except Exception as e:
            self.logger.error(f"Failed to load markets: {e}")
            raise
            
    def get_symbol_info(self, symbol: str) -> Dict:
        """Get information for a specific symbol"""
        try:
            markets = self.exchange.load_markets()
            return markets.get(symbol, {})
        except Exception as e:
            self.logger.error(f"Failed to get symbol info for {symbol}: {e}")
            raise
            
    def calculate_position_size(self, symbol: str, capital: float, price: float) -> float:
        """Calculate position size based on available capital"""
        try:
            market = self.get_symbol_info(symbol)
            
            # Get minimum order size
            min_amount = market.get('limits', {}).get('amount', {}).get('min', 0.001)
            
            # Calculate position size (95% of capital to account for fees)
            position_size = (capital * 0.95) / price
            
            # Get precision
            precision = market.get('precision', {}).get('amount', 8)
            
            # Round to precision
            position_size = round(position_size, precision)
            
            # Ensure it meets minimum
            position_size = max(position_size, min_amount)
            
            self.logger.debug(f"Calculated position size: {position_size} for {capital} capital at {price}")
            return position_size
            
        except Exception as e:
            self.logger.error(f"Failed to calculate position size: {e}")
            raise