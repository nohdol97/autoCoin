"""
Market data fetcher for real-time price and OHLCV data
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import pandas as pd

from ..exchange.binance_client import BinanceClient
from ..logger import get_logger

logger = get_logger('market_data')


class MarketDataFetcher:
    """Fetches and manages market data from exchange"""
    
    def __init__(self, client: BinanceClient, symbol: str):
        self.client = client
        self.symbol = symbol
        self.current_price: Optional[float] = None
        self.last_update: Optional[datetime] = None
        self.price_callbacks: List[Callable] = []
        self.is_running = False
        
        logger.info(f"Initialized MarketDataFetcher for {symbol}")
        
    def subscribe_price_update(self, callback: Callable[[float], None]):
        """Subscribe to price updates"""
        self.price_callbacks.append(callback)
        logger.debug(f"Added price update callback: {callback.__name__}")
        
    def get_current_price(self) -> Optional[float]:
        """Get current cached price"""
        return self.current_price
        
    def fetch_ticker(self) -> Dict[str, Any]:
        """Fetch current ticker data"""
        try:
            ticker = self.client.get_ticker(self.symbol)
            self.current_price = ticker.get('last', 0)
            self.last_update = datetime.now()
            
            # Notify subscribers
            for callback in self.price_callbacks:
                try:
                    callback(self.current_price)
                except Exception as e:
                    logger.error(f"Error in price callback: {e}")
                    
            return ticker
        except Exception as e:
            logger.error(f"Failed to fetch ticker: {e}")
            return {}
            
    def fetch_ohlcv(self, timeframe: str = '1h', limit: int = 100) -> pd.DataFrame:
        """
        Fetch OHLCV data
        
        Args:
            timeframe: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles to fetch
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            ohlcv = self.client.get_ohlcv(self.symbol, timeframe, limit)
            
            if ohlcv.empty:
                logger.warning(f"No OHLCV data received for {self.symbol}")
                return pd.DataFrame()
                
            # Ensure proper column names
            ohlcv.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            
            # Update current price from latest candle
            if not ohlcv.empty:
                self.current_price = ohlcv['close'].iloc[-1]
                self.last_update = datetime.now()
                
            logger.debug(f"Fetched {len(ohlcv)} candles for {self.symbol}")
            return ohlcv
            
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV data: {e}")
            return pd.DataFrame()
            
    async def start_price_stream(self, update_interval: int = 5):
        """
        Start streaming price updates
        
        Args:
            update_interval: Seconds between updates
        """
        self.is_running = True
        logger.info(f"Starting price stream for {self.symbol} "
                   f"(interval: {update_interval}s)")
        
        while self.is_running:
            try:
                # Fetch ticker
                self.fetch_ticker()
                
                # Wait for next update
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                logger.error(f"Error in price stream: {e}")
                await asyncio.sleep(update_interval)
                
    def stop_price_stream(self):
        """Stop price streaming"""
        self.is_running = False
        logger.info(f"Stopping price stream for {self.symbol}")
        
    def get_order_book(self, limit: int = 10) -> Dict[str, Any]:
        """
        Fetch order book data
        
        Args:
            limit: Number of price levels
            
        Returns:
            Order book with bids and asks
        """
        try:
            # CCXT doesn't have a direct order book method in the base interface
            # We'll use fetch_order_book if available
            order_book = self.client.exchange.fetch_order_book(self.symbol, limit)
            
            return {
                'bids': order_book.get('bids', []),
                'asks': order_book.get('asks', []),
                'timestamp': order_book.get('timestamp'),
                'datetime': order_book.get('datetime')
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch order book: {e}")
            return {'bids': [], 'asks': []}
            
    def get_24h_stats(self) -> Dict[str, Any]:
        """Get 24-hour statistics"""
        try:
            ticker = self.fetch_ticker()
            
            return {
                'high': ticker.get('high'),
                'low': ticker.get('low'),
                'volume': ticker.get('baseVolume'),
                'quote_volume': ticker.get('quoteVolume'),
                'change': ticker.get('change'),
                'percentage': ticker.get('percentage'),
                'vwap': ticker.get('vwap'),
                'last': ticker.get('last')
            }
            
        except Exception as e:
            logger.error(f"Failed to get 24h stats: {e}")
            return {}
            
    def calculate_indicators(self, ohlcv: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Calculate basic indicators for quick reference
        
        Args:
            ohlcv: OHLCV DataFrame
            
        Returns:
            Dictionary of indicator series
        """
        indicators = {}
        
        try:
            # Simple Moving Averages
            indicators['sma_20'] = ohlcv['close'].rolling(window=20).mean()
            indicators['sma_50'] = ohlcv['close'].rolling(window=50).mean()
            
            # Volume weighted average price
            indicators['vwap'] = (
                (ohlcv['close'] * ohlcv['volume']).cumsum() / 
                ohlcv['volume'].cumsum()
            )
            
            # Price change
            indicators['change_pct'] = ohlcv['close'].pct_change() * 100
            
            # Volatility (20-period)
            indicators['volatility'] = ohlcv['close'].pct_change().rolling(window=20).std() * 100
            
        except Exception as e:
            logger.error(f"Failed to calculate indicators: {e}")
            
        return indicators