"""
Test Phase 5: Strategy Recommendation System
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.config import Config
from src.recommendation import (
    MarketAnalyzer, MarketCondition,
    PerformanceEvaluator,
    StrategyRecommender,
    StrategySelector
)
from src.strategies import StrategyManager
from src.logger import get_logger

logger = get_logger('test_phase5')


def create_test_ohlcv_data(trend='up', volatility='normal', periods=120):
    """Create test OHLCV data with specific characteristics"""
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='H')
    
    # Base price
    base_price = 50000
    
    # Generate prices based on trend
    if trend == 'up':
        trend_component = np.linspace(0, 0.1, periods)
    elif trend == 'down':
        trend_component = np.linspace(0, -0.1, periods)
    else:  # ranging
        trend_component = np.sin(np.linspace(0, 4*np.pi, periods)) * 0.02
        
    # Add volatility
    if volatility == 'high':
        noise = np.random.normal(0, 0.02, periods)
    elif volatility == 'low':
        noise = np.random.normal(0, 0.002, periods)
    else:
        noise = np.random.normal(0, 0.008, periods)
        
    # Calculate prices
    returns = trend_component + noise
    prices = base_price * (1 + returns).cumprod()
    
    # Create OHLCV
    data = pd.DataFrame({
        'timestamp': dates,
        'open': prices * (1 + np.random.uniform(-0.001, 0.001, periods)),
        'high': prices * (1 + np.random.uniform(0, 0.005, periods)),
        'low': prices * (1 + np.random.uniform(-0.005, 0, periods)),
        'close': prices,
        'volume': np.random.uniform(100, 1000, periods)
    })
    
    return data


def test_market_analyzer():
    """Test market analyzer"""
    logger.info("Testing market analyzer...")
    
    try:
        analyzer = MarketAnalyzer()
        
        # Test trending up market
        data_up = create_test_ohlcv_data(trend='up', volatility='normal')
        analysis_up = analyzer.analyze_market(data_up)
        
        assert 'market_condition' in analysis_up
        assert 'trend' in analysis_up
        assert 'volatility' in analysis_up
        assert 'momentum' in analysis_up
        
        logger.info(f"Trending up analysis: {analysis_up['market_condition'].value}")
        
        # Test ranging market
        data_range = create_test_ohlcv_data(trend='range', volatility='low')
        analysis_range = analyzer.analyze_market(data_range)
        
        logger.info(f"Ranging market analysis: {analysis_range['market_condition'].value}")
        
        # Test market summary
        summary = analyzer.get_market_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0
        
        logger.info("✅ Market analyzer test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Market analyzer test failed: {e}")
        return False


def test_performance_evaluator():
    """Test performance evaluator"""
    logger.info("Testing performance evaluator...")
    
    try:
        evaluator = PerformanceEvaluator()
        
        # Simulate some trades
        trades = [
            {'pnl': 100, 'pnl_percentage': 2.0, 'duration': 3600},
            {'pnl': -50, 'pnl_percentage': -1.0, 'duration': 7200},
            {'pnl': 150, 'pnl_percentage': 3.0, 'duration': 5400},
            {'pnl': 75, 'pnl_percentage': 1.5, 'duration': 4800},
            {'pnl': -25, 'pnl_percentage': -0.5, 'duration': 3000}
        ]
        
        # Update performance for different strategies
        for i, trade in enumerate(trades):
            if i % 2 == 0:
                evaluator.update_performance('breakout', trade, 'TRENDING_UP')
            else:
                evaluator.update_performance('scalping', trade, 'RANGING')
                
        # Test strategy scoring
        breakout_score = evaluator.get_strategy_score('breakout')
        assert 0 <= breakout_score <= 100
        logger.info(f"Breakout strategy score: {breakout_score:.2f}")
        
        scalping_score = evaluator.get_strategy_score('scalping')
        assert 0 <= scalping_score <= 100
        logger.info(f"Scalping strategy score: {scalping_score:.2f}")
        
        # Test best strategy selection
        best = evaluator.get_best_strategy_for_condition(
            'TRENDING_UP', ['breakout', 'scalping', 'trend']
        )
        assert best in ['breakout', 'scalping', 'trend']
        
        # Test performance summary
        summary = evaluator.get_performance_summary()
        assert isinstance(summary, dict)
        assert 'breakout' in summary
        assert 'scalping' in summary
        
        logger.info("✅ Performance evaluator test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Performance evaluator test failed: {e}")
        return False


def test_strategy_recommender():
    """Test strategy recommender"""
    logger.info("Testing strategy recommender...")
    
    try:
        analyzer = MarketAnalyzer()
        evaluator = PerformanceEvaluator()
        recommender = StrategyRecommender(analyzer, evaluator)
        
        # Create test data
        data = create_test_ohlcv_data(trend='up', volatility='normal')
        
        # Get recommendation
        recommendation = recommender.recommend_strategy(
            data, ['breakout', 'scalping', 'trend']
        )
        
        # Check recommendation structure
        assert 'recommended_strategy' in recommendation
        assert 'confidence' in recommendation
        assert 'confidence_level' in recommendation
        assert 'market_condition' in recommendation
        assert 'reasoning' in recommendation
        assert 'scores' in recommendation
        
        logger.info(f"Recommended: {recommendation['recommended_strategy']} "
                   f"(confidence: {recommendation['confidence']:.2f})")
        logger.info(f"Reasoning: {recommendation['reasoning']}")
        
        # Test confidence levels
        assert recommendation['confidence_level'] in ['HIGH', 'MEDIUM', 'LOW']
        assert 0 <= recommendation['confidence'] <= 1
        
        # Test alternatives
        assert 'alternative_strategies' in recommendation
        assert isinstance(recommendation['alternative_strategies'], list)
        
        logger.info("✅ Strategy recommender test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Strategy recommender test failed: {e}")
        return False


def test_strategy_selector():
    """Test strategy selector"""
    logger.info("Testing strategy selector...")
    
    try:
        config = Config()
        strategy_manager = StrategyManager(config.__dict__)
        analyzer = MarketAnalyzer()
        evaluator = PerformanceEvaluator()
        selector = StrategySelector(strategy_manager, analyzer, evaluator)
        
        # Set initial strategy
        strategy_manager.set_active_strategy('breakout')
        
        # Enable auto switching
        selector.enable_auto_switching(True)
        
        # Create test data
        data = create_test_ohlcv_data(trend='range', volatility='normal')
        
        # Evaluate and select
        result = selector.evaluate_and_select(data)
        
        # Check result structure
        assert 'current_strategy' in result
        assert 'recommended_strategy' in result
        assert 'should_switch' in result
        assert 'recommendation' in result
        
        logger.info(f"Current: {result['current_strategy']}, "
                   f"Recommended: {result['recommended_strategy']}")
        
        # Test manual override
        selector.manual_override('scalping', 'Test override')
        assert strategy_manager.active_strategy == 'scalping'
        
        # Test switch history
        history = selector.get_switch_history()
        assert isinstance(history, list)
        assert len(history) > 0
        
        # Test selector stats
        stats = selector.get_selector_stats()
        assert 'auto_switch_enabled' in stats
        assert 'total_switches' in stats
        assert 'current_strategy' in stats
        
        logger.info("✅ Strategy selector test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Strategy selector test failed: {e}")
        return False


def test_market_conditions():
    """Test different market condition detection"""
    logger.info("Testing market condition detection...")
    
    try:
        analyzer = MarketAnalyzer()
        
        conditions_tested = {
            'TRENDING_UP': False,
            'TRENDING_DOWN': False,
            'RANGING': False,
            'VOLATILE': False
        }
        
        # Test trending up
        data = create_test_ohlcv_data(trend='up', volatility='normal', periods=150)
        analysis = analyzer.analyze_market(data)
        condition = analysis['market_condition'].value
        conditions_tested[condition] = True
        logger.info(f"Uptrend test: {condition}")
        
        # Test trending down
        data = create_test_ohlcv_data(trend='down', volatility='normal', periods=150)
        analysis = analyzer.analyze_market(data)
        condition = analysis['market_condition'].value
        conditions_tested[condition] = True
        logger.info(f"Downtrend test: {condition}")
        
        # Test ranging
        data = create_test_ohlcv_data(trend='range', volatility='low', periods=150)
        analysis = analyzer.analyze_market(data)
        condition = analysis['market_condition'].value
        conditions_tested[condition] = True
        logger.info(f"Ranging test: {condition}")
        
        # Test volatile
        data = create_test_ohlcv_data(trend='range', volatility='high', periods=150)
        analysis = analyzer.analyze_market(data)
        condition = analysis['market_condition'].value
        conditions_tested[condition] = True
        logger.info(f"Volatile test: {condition}")
        
        # At least 2 different conditions should be detected
        detected = sum(conditions_tested.values())
        assert detected >= 2, f"Only {detected} conditions detected"
        
        logger.info("✅ Market conditions test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Market conditions test failed: {e}")
        return False


def main():
    """Run Phase 5 tests"""
    logger.info("=== Phase 5 Test Suite ===")
    logger.info("Testing Strategy Recommendation System")
    
    tests = [
        ("Market Analyzer", test_market_analyzer),
        ("Performance Evaluator", test_performance_evaluator),
        ("Strategy Recommender", test_strategy_recommender),
        ("Strategy Selector", test_strategy_selector),
        ("Market Conditions", test_market_conditions),
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
        logger.info("\n🎉 Phase 5 implementation complete!")
        logger.info("Strategy Recommendation System successfully implemented:")
        logger.info("- Market condition analysis (6 conditions)")
        logger.info("- Performance evaluation with scoring")
        logger.info("- Intelligent strategy recommendation")
        logger.info("- Automatic strategy switching")
        logger.info("\nThe system can now automatically select optimal strategies!")
    else:
        logger.error("\n⚠️ Some tests failed. Please check the implementation.")


if __name__ == "__main__":
    main()