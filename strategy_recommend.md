# Phase 5: Strategy Recommendation System ✅

Phase 5 has been successfully implemented with an intelligent strategy recommendation system.

## Implemented Components

### 1. Market Analyzer (`src/recommendation/market_analyzer.py`)
- Comprehensive market condition detection
- 6 market conditions: TRENDING_UP, TRENDING_DOWN, RANGING, VOLATILE, BREAKOUT, CONSOLIDATING
- Technical indicator analysis (ADX, RSI, MACD, Bollinger Bands, ATR)
- Trend strength evaluation
- Volatility analysis
- Pattern detection (breakout, consolidation, reversal)

### 2. Performance Evaluator (`src/recommendation/performance_evaluator.py`)
- Strategy performance tracking and scoring
- Win rate, profit factor, Sharpe ratio calculation
- Maximum drawdown tracking
- Market condition-specific performance analysis
- Recency-weighted scoring
- Performance metrics: 
  - Total P&L, Win/Loss ratio
  - Consecutive wins/losses tracking
  - Recovery factor
  - Risk-adjusted returns

### 3. Strategy Recommender (`src/recommendation/strategy_recommender.py`)
- Multi-factor strategy scoring algorithm
- Suitability matrix for strategy-market alignment
- Confidence calculation
- Human-readable reasoning generation
- Alternative strategy suggestions
- Score components:
  - Market condition suitability (40%)
  - Historical performance (30%)
  - Current market alignment (20%)
  - Risk assessment (10%)

### 4. Strategy Selector (`src/recommendation/strategy_selector.py`)
- Automatic strategy switching capability
- Switch decision logic with constraints
- Manual override support
- Switch history tracking
- Performance-based switching triggers
- Safety features:
  - Minimum trades before switch
  - Minimum time between switches
  - No switching with open positions

## Market Conditions

### Detection Criteria
1. **TRENDING_UP**: Strong upward price movement with ADX > 25
2. **TRENDING_DOWN**: Strong downward price movement with ADX > 25
3. **RANGING**: Low volatility, price oscillating in range
4. **VOLATILE**: High ATR, large price swings
5. **BREAKOUT**: Price breaking key resistance/support levels
6. **CONSOLIDATING**: Low volatility, tight price range

### Strategy Suitability Matrix
```
             BREAKOUT  TREND_UP  TREND_DN  VOLATILE  RANGING  CONSOLIDATE
Breakout:      0.9       0.8       0.7       0.6      0.3        0.4
Scalping:      0.3       0.4       0.4       0.8      0.9        0.7
Trend:         0.7       0.95      0.9       0.5      0.2        0.2
```

## Recommendation Algorithm

### Scoring Process
1. **Market Analysis**: Identify current market condition
2. **Performance Lookup**: Get historical performance for each strategy
3. **Alignment Check**: Evaluate strategy-market alignment
4. **Risk Assessment**: Consider current volatility and risk
5. **Confidence Calculation**: Determine recommendation confidence
6. **Reasoning Generation**: Create human-readable explanation

### Confidence Levels
- **HIGH** (≥ 0.8): Strong recommendation, clear market conditions
- **MEDIUM** (≥ 0.6): Moderate confidence, reasonable clarity
- **LOW** (< 0.6): Uncertain conditions, use with caution

## Automatic Strategy Switching

### Switch Triggers
- Performance degradation (3+ consecutive losses)
- Market condition change with high confidence
- Significant score improvement (> 15%)

### Switch Constraints
- Minimum 5 trades before switching
- Minimum 4 hours between switches
- No switching with open positions
- Confidence threshold > 0.7

## Usage Example

```python
# Initialize components
analyzer = MarketAnalyzer()
evaluator = PerformanceEvaluator()
selector = StrategySelector(strategy_manager, analyzer, evaluator)

# Enable automatic switching
selector.enable_auto_switching(True)

# Get recommendation
result = selector.evaluate_and_select(ohlcv_data)
print(f"Recommended: {result['recommended_strategy']}")
print(f"Confidence: {result['recommendation']['confidence']:.2f}")
print(f"Reasoning: {result['recommendation']['reasoning']}")

# Manual override if needed
selector.manual_override('scalping', 'Market conditions unclear')
```

## Test Results
All Phase 5 tests passed:
- ✅ Market Analyzer
- ✅ Performance Evaluator
- ✅ Strategy Recommender
- ✅ Strategy Selector
- ✅ Market Conditions

## Key Features
1. **Intelligent Analysis**: Multi-factor scoring considering market conditions, performance, and risk
2. **Adaptive Selection**: Automatically adjusts strategy based on changing conditions
3. **Performance Tracking**: Continuous evaluation of strategy effectiveness
4. **Safety First**: Conservative switching with multiple safeguards
5. **Transparency**: Clear reasoning for all recommendations

## Next Steps
Phase 6: Integration & Optimization
- Integrate recommendation system with trading engine
- Add real-time performance monitoring
- Implement advanced risk management
- Optimize for production deployment

The strategy recommendation system is now ready to intelligently select optimal trading strategies!