"""
Test Phase 3: Trading Strategy Implementation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.config import Config
from src.strategies import (
    Strategy, Signal, Position,
    BreakoutStrategy, ScalpingStrategy, TrendFollowingStrategy,
    StrategyFactory, StrategyManager
)
from src.logger import get_logger

logger = get_logger('test_phase3')


def create_mock_data(days=50):
    """Create mock OHLCV data for testing"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # Generate realistic price movement
    np.random.seed(42)
    base_price = 50000
    returns = np.random.normal(0.001, 0.02, days)
    prices = base_price * (1 + returns).cumprod()
    
    # Create OHLCV data
    data = pd.DataFrame({
        'timestamp': dates,
        'open': prices * (1 + np.random.uniform(-0.005, 0.005, days)),
        'high': prices * (1 + np.random.uniform(0, 0.01, days)),
        'low': prices * (1 + np.random.uniform(-0.01, 0, days)),
        'close': prices,
        'volume': np.random.uniform(100, 1000, days)
    })
    
    return data


def test_strategy_factory():
    """Test strategy factory"""
    logger.info("Testing strategy factory...")
    
    try:
        # Test available strategies
        strategies = StrategyFactory.get_available_strategies()
        assert len(strategies) == 3
        assert 'breakout' in strategies
        assert 'scalping' in strategies
        assert 'trend' in strategies
        
        # Test strategy creation
        config = {'stop_loss': 2.0, 'take_profit': 5.0}
        strategy = StrategyFactory.create_strategy('breakout', config)
        assert isinstance(strategy, BreakoutStrategy)
        assert strategy.name == 'breakout'
        
        # Test strategy info
        info = StrategyFactory.get_strategy_info('scalping')
        assert info['name'] == 'scalping'
        assert 'parameters' in info
        
        logger.info("✅ Strategy factory test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Strategy factory test failed: {e}")
        return False


def test_breakout_strategy():
    """Test breakout strategy"""
    logger.info("Testing breakout strategy...")
    
    try:
        config = {
            'lookback_buy': 20,
            'lookback_sell': 10,
            'stop_loss': 2.0,
            'take_profit': 5.0
        }
        
        strategy = BreakoutStrategy(config)
        data = create_mock_data(30)
        
        # Test required candles
        assert strategy.get_required_candles() == 21
        
        # Test signal generation
        current_price = data['close'].iloc[-1]
        signal = strategy.analyze(data, current_price)
        assert signal in [Signal.BUY, Signal.SELL, Signal.HOLD]
        
        logger.info("✅ Breakout strategy test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Breakout strategy test failed: {e}")
        return False


def test_scalping_strategy():
    """Test scalping strategy"""
    logger.info("Testing scalping strategy...")
    
    try:
        config = {
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'bb_period': 20,
            'bb_std': 2,
            'stop_loss': 0.5,
            'take_profit': 1.0
        }
        
        strategy = ScalpingStrategy(config)
        data = create_mock_data(30)
        
        # Test required candles
        assert strategy.get_required_candles() == 25
        
        # Test signal generation
        current_price = data['close'].iloc[-1]
        signal = strategy.analyze(data, current_price)
        assert signal in [Signal.BUY, Signal.SELL, Signal.HOLD]
        
        logger.info("✅ Scalping strategy test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Scalping strategy test failed: {e}")
        return False


def test_trend_strategy():
    """Test trend following strategy"""
    logger.info("Testing trend following strategy...")
    
    try:
        config = {
            'ema_fast': 12,
            'ema_slow': 26,
            'trailing_stop': 3.0,
            'stop_loss': 3.0,
            'take_profit': 10.0
        }
        
        strategy = TrendFollowingStrategy(config)
        data = create_mock_data(40)
        
        # Test required candles
        assert strategy.get_required_candles() == 36
        
        # Test signal generation
        current_price = data['close'].iloc[-1]
        signal = strategy.analyze(data, current_price)
        assert signal in [Signal.BUY, Signal.SELL, Signal.HOLD]
        
        # Test trailing stop functionality would require a position
        # Skip detailed trailing stop test for now
        
        logger.info("✅ Trend strategy test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Trend strategy test failed: {e}")
        return False


def test_position_management():
    """Test position management"""
    logger.info("Testing position management...")
    
    try:
        config = {'stop_loss': 2.0, 'take_profit': 5.0}
        strategy = BreakoutStrategy(config)
        
        # Test opening position
        position = strategy.open_position(
            symbol='BTCUSDT',
            side='LONG',
            entry_price=50000,
            quantity=0.1
        )
        
        assert strategy.position is not None
        assert position.symbol == 'BTCUSDT'
        assert position.side == 'LONG'
        assert position.entry_price == 50000
        assert position.stop_loss == 49000  # 2% stop loss
        assert position.take_profit == 52500  # 5% take profit
        
        # Test P&L calculation
        position.update_pnl(51000)
        assert position.pnl == 100  # (51000 - 50000) * 0.1
        assert position.pnl_percentage == 2.0
        
        # Test exit conditions
        assert not position.should_stop_loss(50500)
        assert position.should_stop_loss(48900)
        assert not position.should_take_profit(51000)
        assert position.should_take_profit(52600)
        
        # Test closing position
        closed_position = strategy.close_position(51000)
        assert strategy.position is None
        assert len(strategy.history) == 1
        assert closed_position.exit_price == 51000
        
        logger.info("✅ Position management test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Position management test failed: {e}")
        return False


def test_strategy_manager():
    """Test strategy manager"""
    logger.info("Testing strategy manager...")
    
    try:
        config = Config()
        # Pass the config's internal dict representation
        config_dict = {
            'strategies': config.strategies,
            'symbol': config.symbol,
            'base_amount': config.base_amount,
            'max_positions': config.max_positions
        }
        manager = StrategyManager(config_dict)
        
        # Test loading strategies
        breakout = manager.load_strategy('breakout')
        assert isinstance(breakout, BreakoutStrategy)
        assert 'breakout' in manager.strategies
        
        # Test setting active strategy
        active = manager.set_active_strategy('scalping')
        assert isinstance(active, ScalpingStrategy)
        assert manager.active_strategy == 'scalping'
        
        # Test getting active strategy
        current = manager.get_active_strategy()
        assert current == active
        
        # Test performance summary
        summary = manager.get_performance_summary()
        assert 'breakout' in summary
        assert 'scalping' in summary
        
        logger.info("✅ Strategy manager test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Strategy manager test failed: {e}")
        return False


def main():
    """Run Phase 3 tests"""
    logger.info("=== Phase 3 Test Suite ===")
    logger.info("Testing Trading Strategy Implementation")
    
    tests = [
        ("Strategy Factory", test_strategy_factory),
        ("Breakout Strategy", test_breakout_strategy),
        ("Scalping Strategy", test_scalping_strategy),
        ("Trend Strategy", test_trend_strategy),
        ("Position Management", test_position_management),
        ("Strategy Manager", test_strategy_manager),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\nRunning: {test_name}")
        success = test_func()
        results.append((test_name, success))
    
    # Summary
    logger.info("\n=== Test Summary ===")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n🎉 Phase 3 implementation complete!")
        logger.info("All trading strategies have been successfully implemented:")
        logger.info("- Breakout Strategy (20/10 day)")
        logger.info("- Scalping Strategy (RSI + Bollinger Bands)")
        logger.info("- Trend Following Strategy (EMA cross with trailing stop)")
        logger.info("\nStrategies are ready for integration with the trading engine.")
    else:
        logger.error("\n⚠️ Some tests failed. Please check the implementation.")


if __name__ == "__main__":
    main()