"""
Binance Futures API Client
Extended client for futures trading functionality
"""
import asyncio
from typing import Dict, List, Optional, Tuple, Union
import logging
from datetime import datetime, timedelta
import pandas as pd
from decimal import Decimal
from .binance_client import BinanceClient


class BinanceFuturesClient(BinanceClient):
    """Extended Binance client with futures trading support"""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        super().__init__(api_key, api_secret, testnet)
        self.futures_exchange = None
        self._initialize_futures()
        
    def _initialize_futures(self):
        """Initialize futures trading"""
        try:
            # Create a separate instance for futures
            import ccxt
            
            if self.testnet:
                self.futures_exchange = ccxt.binance({
                    'apiKey': self.exchange.apiKey,
                    'secret': self.exchange.secret,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'future',
                        'test': True,
                    }
                })
                # Set testnet URLs for futures
                self.futures_exchange.urls['api'] = {
                    'fapiPublic': 'https://testnet.binancefuture.com/fapi/v1',
                    'fapiPrivate': 'https://testnet.binancefuture.com/fapi/v1',
                }
                self.logger.info("Initialized Binance Futures client in TESTNET mode")
            else:
                self.futures_exchange = ccxt.binance({
                    'apiKey': self.exchange.apiKey,
                    'secret': self.exchange.secret,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'future',
                    }
                })
                self.logger.info("Initialized Binance Futures client in LIVE mode")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize futures client: {e}")
            raise
            
    async def initialize(self):
        """Async initialization"""
        try:
            # Load markets for both spot and futures
            await asyncio.gather(
                asyncio.to_thread(self.exchange.load_markets),
                asyncio.to_thread(self.futures_exchange.load_markets)
            )
            self.logger.info("Markets loaded for spot and futures")
        except Exception as e:
            self.logger.error(f"Failed to initialize markets: {e}")
            raise
            
    async def close(self):
        """Close connections"""
        pass  # ccxt doesn't require explicit closing
        
    async def test_connection(self):
        """Test API connection"""
        try:
            # Test both spot and futures
            spot_time = await asyncio.to_thread(self.exchange.fetch_time)
            futures_time = await asyncio.to_thread(self.futures_exchange.fetch_time)
            self.logger.info(f"API connection successful - Spot: {spot_time}, Futures: {futures_time}")
            return True
        except Exception as e:
            self.logger.error(f"API connection test failed: {e}")
            return False
            
    # Futures-specific methods
    
    def get_futures_balance(self) -> Dict:
        """Get futures account balance"""
        try:
            balance = self.futures_exchange.fetch_balance()
            self.logger.debug(f"Fetched futures balance: {balance}")
            return balance
        except Exception as e:
            self.logger.error(f"Failed to fetch futures balance: {e}")
            raise
            
    def get_futures_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get current futures positions"""
        try:
            positions = self.futures_exchange.fetch_positions(symbol)
            self.logger.debug(f"Found {len(positions)} futures positions")
            return positions
        except Exception as e:
            self.logger.error(f"Failed to fetch futures positions: {e}")
            raise
            
    def set_leverage(self, symbol: str, leverage: int) -> Dict:
        """Set leverage for a futures symbol"""
        try:
            result = self.futures_exchange.set_leverage(leverage, symbol)
            self.logger.info(f"Set leverage to {leverage}x for {symbol}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to set leverage: {e}")
            raise
            
    def set_margin_mode(self, symbol: str, margin_mode: str = 'isolated') -> Dict:
        """Set margin mode (cross/isolated)"""
        try:
            result = self.futures_exchange.set_margin_mode(margin_mode, symbol)
            self.logger.info(f"Set margin mode to {margin_mode} for {symbol}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to set margin mode: {e}")
            raise
            
    def create_futures_order(self, symbol: str, order_type: str, side: str, 
                           amount: float, price: Optional[float] = None, 
                           stop_loss: Optional[float] = None,
                           take_profit: Optional[float] = None,
                           params: Dict = None) -> Dict:
        """Create a futures order with optional SL/TP"""
        try:
            if params is None:
                params = {}
                
            # Main order
            order = self.futures_exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
                params=params
            )
            
            self.logger.info(f"Created futures {side} order for {amount} {symbol}")
            
            # Create stop loss if specified
            if stop_loss:
                sl_side = 'sell' if side == 'buy' else 'buy'
                sl_order = self.futures_exchange.create_order(
                    symbol=symbol,
                    type='stop_market',
                    side=sl_side,
                    amount=amount,
                    stopPrice=stop_loss,
                    params={'stopPrice': stop_loss, 'workingType': 'MARK_PRICE'}
                )
                self.logger.info(f"Created stop loss at {stop_loss}")
                order['stop_loss'] = sl_order
                
            # Create take profit if specified
            if take_profit:
                tp_side = 'sell' if side == 'buy' else 'buy'
                tp_order = self.futures_exchange.create_order(
                    symbol=symbol,
                    type='take_profit_market',
                    side=tp_side,
                    amount=amount,
                    stopPrice=take_profit,
                    params={'stopPrice': take_profit, 'workingType': 'MARK_PRICE'}
                )
                self.logger.info(f"Created take profit at {take_profit}")
                order['take_profit'] = tp_order
                
            return order
            
        except Exception as e:
            self.logger.error(f"Failed to create futures order: {e}")
            raise
            
    def close_futures_position(self, symbol: str) -> Dict:
        """Close a futures position"""
        try:
            positions = self.get_futures_positions(symbol)
            if not positions:
                self.logger.warning(f"No position found for {symbol}")
                return {'status': 'no_position'}
                
            position = positions[0]
            contracts = abs(position['contracts'])
            side = 'sell' if position['side'] == 'long' else 'buy'
            
            order = self.futures_exchange.create_market_order(symbol, side, contracts)
            self.logger.info(f"Closed position for {symbol}")
            return order
            
        except Exception as e:
            self.logger.error(f"Failed to close futures position: {e}")
            raise
            
    def get_funding_rate(self, symbol: str) -> Dict:
        """Get current funding rate"""
        try:
            funding = self.futures_exchange.fetch_funding_rate(symbol)
            self.logger.debug(f"Funding rate for {symbol}: {funding}")
            return funding
        except Exception as e:
            self.logger.error(f"Failed to fetch funding rate: {e}")
            raise
            
    def get_funding_history(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get funding rate history"""
        try:
            history = self.futures_exchange.fetch_funding_rate_history(symbol, limit=limit)
            self.logger.debug(f"Fetched {len(history)} funding rate records")
            return history
        except Exception as e:
            self.logger.error(f"Failed to fetch funding history: {e}")
            raise
            
    def get_mark_price(self, symbol: str) -> float:
        """Get mark price for a symbol"""
        try:
            ticker = self.futures_exchange.fetch_ticker(symbol)
            mark_price = ticker.get('info', {}).get('markPrice')
            if mark_price:
                return float(mark_price)
            return ticker['last']  # Fallback to last price
        except Exception as e:
            self.logger.error(f"Failed to fetch mark price: {e}")
            raise
            
    def get_liquidation_price(self, symbol: str) -> Optional[float]:
        """Get liquidation price for current position"""
        try:
            positions = self.get_futures_positions(symbol)
            if not positions:
                return None
                
            position = positions[0]
            return position.get('liquidationPrice')
            
        except Exception as e:
            self.logger.error(f"Failed to get liquidation price: {e}")
            return None
            
    def calculate_futures_position_size(self, symbol: str, capital: float, 
                                      leverage: int, price: float) -> float:
        """Calculate futures position size based on capital and leverage"""
        try:
            market = self.futures_exchange.market(symbol)
            
            # Calculate notional value
            notional = capital * leverage
            
            # Calculate contracts
            contract_size = market.get('contractSize', 1)
            contracts = notional / (price * contract_size)
            
            # Apply precision
            precision = market.get('precision', {}).get('amount', 3)
            contracts = round(contracts, precision)
            
            # Check minimum
            min_contracts = market.get('limits', {}).get('amount', {}).get('min', 0.001)
            contracts = max(contracts, min_contracts)
            
            self.logger.debug(f"Calculated {contracts} contracts for {capital} capital at {leverage}x leverage")
            return contracts
            
        except Exception as e:
            self.logger.error(f"Failed to calculate futures position size: {e}")
            raise
            
    def get_max_leverage(self, symbol: str) -> int:
        """Get maximum allowed leverage for a symbol"""
        try:
            market = self.futures_exchange.market(symbol)
            max_leverage = market.get('info', {}).get('maxLeverage', 20)
            return int(max_leverage)
        except Exception as e:
            self.logger.error(f"Failed to get max leverage: {e}")
            return 20  # Default max leverage
            
    def get_futures_ticker(self, symbol: str) -> Dict:
        """Get futures ticker information"""
        try:
            ticker = self.futures_exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            self.logger.error(f"Failed to fetch futures ticker: {e}")
            raise
            
    def get_futures_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> pd.DataFrame:
        """Get futures OHLCV data"""
        try:
            ohlcv = self.futures_exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            self.logger.debug(f"Fetched {len(df)} futures candles for {symbol}")
            return df
        except Exception as e:
            self.logger.error(f"Failed to fetch futures OHLCV: {e}")
            raise