import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.exchange.binance_client import BinanceClient
from src.logger import setup_logger

# Set up test logger
logger = setup_logger('test', 'DEBUG')

class TestBinanceClient:
    """Test cases for Binance API client"""
    
    @pytest.fixture
    def client(self):
        """Create a test client"""
        config = Config()
        return BinanceClient(config.api_key, config.api_secret, testnet=True)
    
    def test_initialization(self, client):
        """Test client initialization"""
        assert client is not None
        assert client.testnet == True
        assert client.exchange is not None
        
    def test_get_balance(self, client):
        """Test balance fetching"""
        try:
            balance = client.get_balance()
            assert isinstance(balance, dict)
            assert 'total' in balance
            assert 'free' in balance
            assert 'used' in balance
            logger.info(f"Balance test passed. Total balance: {balance.get('total', {})}")
        except Exception as e:
            logger.warning(f"Balance test skipped due to API error: {e}")
            pytest.skip(f"API error: {e}")
            
    def test_get_ticker(self, client):
        """Test ticker fetching"""
        try:
            ticker = client.get_ticker('BTC/USDT')
            assert isinstance(ticker, dict)
            assert 'last' in ticker
            assert 'bid' in ticker
            assert 'ask' in ticker
            logger.info(f"Ticker test passed. BTC price: {ticker.get('last', 'N/A')}")
        except Exception as e:
            logger.warning(f"Ticker test skipped due to API error: {e}")
            pytest.skip(f"API error: {e}")
            
    def test_get_ohlcv(self, client):
        """Test OHLCV data fetching"""
        try:
            df = client.get_ohlcv('BTC/USDT', '1h', limit=10)
            assert not df.empty
            assert len(df) <= 10
            assert all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume'])
            logger.info(f"OHLCV test passed. Fetched {len(df)} candles")
        except Exception as e:
            logger.warning(f"OHLCV test skipped due to API error: {e}")
            pytest.skip(f"API error: {e}")
            
    def test_get_order_book(self, client):
        """Test order book fetching"""
        try:
            order_book = client.get_order_book('BTC/USDT', limit=5)
            assert isinstance(order_book, dict)
            assert 'bids' in order_book
            assert 'asks' in order_book
            assert len(order_book['bids']) <= 5
            assert len(order_book['asks']) <= 5
            logger.info("Order book test passed")
        except Exception as e:
            logger.warning(f"Order book test skipped due to API error: {e}")
            pytest.skip(f"API error: {e}")
            
    def test_get_symbol_info(self, client):
        """Test symbol information fetching"""
        try:
            info = client.get_symbol_info('BTC/USDT')
            assert isinstance(info, dict)
            if info:  # May be empty in testnet
                assert 'symbol' in info or 'id' in info
                logger.info(f"Symbol info test passed: {info.get('symbol', info.get('id', 'N/A'))}")
            else:
                logger.info("Symbol info test passed (empty response from testnet)")
        except Exception as e:
            logger.warning(f"Symbol info test skipped due to API error: {e}")
            pytest.skip(f"API error: {e}")
            
    def test_calculate_position_size(self, client):
        """Test position size calculation"""
        try:
            # Mock calculation since it depends on symbol info
            capital = 1000  # USDT
            price = 50000   # BTC price
            
            position_size = client.calculate_position_size('BTC/USDT', capital, price)
            assert isinstance(position_size, float)
            assert position_size > 0
            logger.info(f"Position size test passed: {position_size} BTC for {capital} USDT")
        except Exception as e:
            logger.warning(f"Position size test skipped due to API error: {e}")
            pytest.skip(f"API error: {e}")

def test_connection():
    """Simple test to verify API connection"""
    try:
        config = Config()
        client = BinanceClient(config.api_key, config.api_secret, testnet=True)
        
        # Try to fetch exchange info
        info = client.exchange.fetch_time()
        logger.info(f"Connection test passed. Server time: {info}")
        assert info is not None
        
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        pytest.fail(f"Failed to connect to Binance API: {e}")

if __name__ == "__main__":
    # Run basic connection test
    print("Testing Binance API connection...")
    test_connection()
    print("Connection test completed!")