"""
Integration tests for futures trading functionality
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.futures_config import FuturesConfig
from src.exchange.binance_futures_client import BinanceFuturesClient
from src.trading.futures_position_manager import FuturesPositionManager
from src.trading.futures_engine import FuturesTradingEngine
from src.trading.futures_types import FuturesPosition, PositionSide, MarginMode
from src.utils.risk_manager import RiskManager


class TestFuturesIntegration:
    """Test futures trading integration"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        config = FuturesConfig()
        config.use_testnet = True
        config.enable_futures = True
        config.default_leverage = 5
        config.max_leverage = 20
        return config
        
    @pytest.fixture
    def mock_futures_client(self):
        """Create mock futures client"""
        client = Mock(spec=BinanceFuturesClient)
        client.initialize = AsyncMock()
        client.close = AsyncMock()
        client.test_connection = AsyncMock(return_value=True)
        
        # Mock balance
        client.get_futures_balance = Mock(return_value={
            'USDT': {
                'total': 10000,
                'free': 8000,
                'used': 2000
            }
        })
        
        # Mock positions
        client.get_futures_positions = Mock(return_value=[])
        
        # Mock ticker
        client.get_futures_ticker = Mock(return_value={
            'last': 50000,
            'bid': 49990,
            'ask': 50010
        })
        
        return client
        
    @pytest.fixture
    def risk_manager(self, config):
        """Create risk manager"""
        return RiskManager(config.risk_percentage)
        
    @pytest.fixture
    async def position_manager(self, mock_futures_client, risk_manager):
        """Create position manager"""
        manager = FuturesPositionManager(mock_futures_client, risk_manager)
        await manager.initialize()
        return manager
        
    @pytest.fixture
    async def futures_engine(self, config):
        """Create futures trading engine"""
        with patch('src.trading.futures_engine.BinanceFuturesClient') as mock_client:
            mock_client.return_value = Mock()
            mock_client.return_value.initialize = AsyncMock()
            
            engine = FuturesTradingEngine(config)
            await engine.initialize()
            return engine
            
    @pytest.mark.asyncio
    async def test_futures_client_initialization(self, mock_futures_client):
        """Test futures client initialization"""
        await mock_futures_client.initialize()
        connected = await mock_futures_client.test_connection()
        
        assert connected is True
        mock_futures_client.initialize.assert_called_once()
        mock_futures_client.test_connection.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_position_manager_open_position(self, position_manager, mock_futures_client):
        """Test opening a futures position"""
        # Mock methods
        mock_futures_client.set_leverage = Mock()
        mock_futures_client.set_margin_mode = Mock()
        mock_futures_client.create_futures_order = Mock(return_value={
            'id': '12345',
            'symbol': 'BTC/USDT',
            'side': 'buy',
            'amount': 0.1,
            'status': 'filled'
        })
        
        # Open position
        result = await position_manager.open_position(
            symbol='BTC/USDT',
            side='buy',
            size=0.1,
            leverage=10
        )
        
        assert result['id'] == '12345'
        mock_futures_client.set_leverage.assert_called_with('BTC/USDT', 10)
        mock_futures_client.create_futures_order.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_position_manager_risk_metrics(self, position_manager):
        """Test risk metrics calculation"""
        # Mock position
        position = FuturesPosition(
            symbol='BTC/USDT',
            side=PositionSide.LONG,
            contracts=0.1,
            entry_price=50000,
            mark_price=51000,
            liquidation_price=45000,
            unrealized_pnl=100,
            realized_pnl=0,
            margin=500,
            leverage=10,
            margin_mode=MarginMode.ISOLATED,
            timestamp=datetime.now()
        )
        
        position_manager.positions['BTC/USDT'] = position
        
        # Get risk metrics
        risk_metrics = await position_manager.get_risk_metrics()
        
        assert risk_metrics.positions_count == 1
        assert risk_metrics.total_notional == 5100  # 0.1 * 51000
        assert risk_metrics.current_leverage > 0
        
    @pytest.mark.asyncio
    async def test_liquidation_risk_check(self, position_manager):
        """Test liquidation risk checking"""
        # Mock high-risk position
        position = FuturesPosition(
            symbol='BTC/USDT',
            side=PositionSide.LONG,
            contracts=0.1,
            entry_price=50000,
            mark_price=46000,  # Close to liquidation
            liquidation_price=45000,
            unrealized_pnl=-400,
            realized_pnl=0,
            margin=500,
            leverage=10,
            margin_mode=MarginMode.ISOLATED,
            timestamp=datetime.now()
        )
        
        position_manager.positions['BTC/USDT'] = position
        
        # Check liquidation risk
        at_risk = await position_manager.check_liquidation_risk()
        
        assert len(at_risk) == 1
        assert at_risk[0]['symbol'] == 'BTC/USDT'
        assert at_risk[0]['risk_level'] in ['MEDIUM', 'HIGH']
        
    @pytest.mark.asyncio
    async def test_funding_rate_strategy(self, futures_engine):
        """Test funding rate arbitrage strategy"""
        # Set funding arbitrage strategy
        assert futures_engine.set_strategy('funding_arbitrage')
        
        # Get strategy
        strategy = futures_engine.strategies['funding_arbitrage']
        
        # Mock funding rate
        mock_client = Mock()
        mock_client.get_funding_rate = AsyncMock(return_value={
            'symbol': 'BTC/USDT',
            'fundingRate': 0.01,  # 1% funding
            'timestamp': datetime.now().timestamp() * 1000,
            'fundingDatetime': (datetime.now().timestamp() + 3600) * 1000
        })
        
        mock_client.get_futures_ticker = AsyncMock(return_value={
            'last': 50000
        })
        
        mock_client.get_ticker = AsyncMock(return_value={
            'last': 49900  # Spot price lower = futures premium
        })
        
        # Analyze
        signal = await strategy.analyze(mock_client, 'BTC/USDT')
        
        assert signal['signal'] in ['short_arbitrage', 'hold']
        assert 'funding_rate' in signal
        assert 'annual_funding' in signal
        
    @pytest.mark.asyncio
    async def test_grid_trading_strategy(self, futures_engine):
        """Test grid trading strategy"""
        # Set grid trading strategy
        assert futures_engine.set_strategy('grid_trading')
        
        strategy = futures_engine.strategies['grid_trading']
        
        # Mock OHLCV data
        import pandas as pd
        ohlcv_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='h'),
            'open': [50000 + i * 10 for i in range(100)],
            'high': [50050 + i * 10 for i in range(100)],
            'low': [49950 + i * 10 for i in range(100)],
            'close': [50000 + i * 10 for i in range(100)],
            'volume': [100] * 100
        })
        ohlcv_data.set_index('timestamp', inplace=True)
        
        mock_client = Mock()
        mock_client.get_futures_ticker = AsyncMock(return_value={'last': 50500})
        mock_client.get_futures_ohlcv = AsyncMock(return_value=ohlcv_data)
        
        # Analyze
        signal = await strategy.analyze(mock_client, 'BTC/USDT')
        
        assert signal['signal'] in ['create_grid', 'maintain_grid', 'hold']
        assert 'grid_levels' in signal
        assert 'confidence' in signal
        
    @pytest.mark.asyncio
    async def test_long_short_switching_strategy(self, futures_engine):
        """Test long-short switching strategy"""
        # Set strategy
        assert futures_engine.set_strategy('long_short_switching')
        
        strategy = futures_engine.strategies['long_short_switching']
        
        # Mock trending market data
        import pandas as pd
        import numpy as np
        
        # Create uptrend data
        prices = []
        base = 50000
        for i in range(100):
            prices.append(base + i * 50 + np.random.randn() * 100)
            
        ohlcv_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='15min'),
            'open': prices,
            'high': [p + 50 for p in prices],
            'low': [p - 50 for p in prices],
            'close': prices,
            'volume': [100 + np.random.randn() * 10 for _ in range(100)]
        })
        ohlcv_data.set_index('timestamp', inplace=True)
        
        mock_client = Mock()
        mock_client.get_futures_ticker = AsyncMock(return_value={'last': prices[-1]})
        mock_client.get_futures_ohlcv = AsyncMock(return_value=ohlcv_data)
        mock_client.get_futures_positions = AsyncMock(return_value=[])
        
        # Analyze
        signal = await strategy.analyze(mock_client, 'BTC/USDT')
        
        assert signal['signal'] in ['open_long', 'open_short', 'hold', 'close_position']
        assert 'direction' in signal
        assert 'trend_score' in signal
        
    @pytest.mark.asyncio
    async def test_volatility_breakout_strategy(self, futures_engine):
        """Test volatility breakout strategy"""
        # Set strategy
        assert futures_engine.set_strategy('volatility_breakout')
        
        strategy = futures_engine.strategies['volatility_breakout']
        
        # Mock low volatility then breakout data
        import pandas as pd
        import numpy as np
        
        # Create squeeze then breakout pattern
        prices = []
        base = 50000
        
        # Low volatility period
        for i in range(80):
            prices.append(base + np.random.randn() * 50)
            
        # Breakout
        for i in range(20):
            prices.append(base + 500 + i * 100)
            
        ohlcv_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='h'),
            'open': prices,
            'high': [p + 20 for p in prices[:80]] + [p + 100 for p in prices[80:]],
            'low': [p - 20 for p in prices[:80]] + [p - 50 for p in prices[80:]],
            'close': prices,
            'volume': [50] * 80 + [200] * 20  # Volume spike on breakout
        })
        ohlcv_data.set_index('timestamp', inplace=True)
        
        mock_client = Mock()
        mock_client.get_futures_ticker = AsyncMock(return_value={'last': prices[-1]})
        mock_client.get_futures_ohlcv = AsyncMock(return_value=ohlcv_data)
        
        # Analyze
        signal = await strategy.analyze(mock_client, 'BTC/USDT')
        
        assert signal['signal'] in ['long_breakout', 'short_breakout', 'hold']
        assert 'volatility_percentile' in signal
        assert 'squeeze_count' in signal
        
    @pytest.mark.asyncio
    async def test_emergency_close_all_positions(self, position_manager, mock_futures_client):
        """Test emergency close all positions"""
        # Mock positions
        positions = [
            {
                'symbol': 'BTC/USDT',
                'contracts': 0.1,
                'side': 'long',
                'entryPrice': 50000,
                'markPrice': 49000,
                'unrealizedPnl': -100
            },
            {
                'symbol': 'ETH/USDT',
                'contracts': 1.0,
                'side': 'short',
                'entryPrice': 3000,
                'markPrice': 3100,
                'unrealizedPnl': -100
            }
        ]
        
        mock_futures_client.get_futures_positions = Mock(return_value=positions)
        mock_futures_client.close_futures_position = AsyncMock(return_value={
            'status': 'closed'
        })
        
        # Update positions
        await position_manager.update_positions()
        
        # Emergency close
        results = await position_manager.emergency_close_all()
        
        assert len(results) == 2
        assert all(r['status'] == 'closed' for r in results)
        
    @pytest.mark.asyncio
    async def test_trading_engine_lifecycle(self, futures_engine):
        """Test trading engine start/stop lifecycle"""
        # Set strategy
        futures_engine.set_strategy('funding_arbitrage')
        
        # Mock the trading loop to prevent actual trading
        futures_engine.trading_loop = AsyncMock()
        futures_engine.position_monitoring_loop = AsyncMock()
        futures_engine.risk_monitoring_loop = AsyncMock()
        futures_engine.funding_monitoring_loop = AsyncMock()
        
        # Start engine
        start_task = asyncio.create_task(futures_engine.start())
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        # Stop engine
        await futures_engine.stop()
        
        # Ensure tasks are cancelled
        assert not futures_engine.is_running
        assert len(futures_engine._tasks) == 0
        
        # Cancel start task
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass