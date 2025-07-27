"""
Strategy selector with automatic switching capabilities
"""

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import asyncio

from .market_analyzer import MarketAnalyzer
from .performance_evaluator import PerformanceEvaluator
from .strategy_recommender import StrategyRecommender
from ..strategies import StrategyManager
from ..logger import get_logger

logger = get_logger('strategy_selector')


class StrategySelector:
    """Automatic strategy selection and switching system"""
    
    def __init__(self, 
                 strategy_manager: StrategyManager,
                 market_analyzer: MarketAnalyzer,
                 performance_evaluator: PerformanceEvaluator):
        self.strategy_manager = strategy_manager
        self.market_analyzer = market_analyzer
        self.performance_evaluator = performance_evaluator
        
        # Create recommender
        self.recommender = StrategyRecommender(market_analyzer, performance_evaluator)
        
        # Configuration
        self.auto_switch_enabled = False
        self.min_trades_before_switch = 5
        self.min_time_before_switch = timedelta(hours=4)
        self.confidence_threshold = 0.7
        self.improvement_threshold = 0.15
        
        # State tracking
        self.last_switch_time: Optional[datetime] = None
        self.current_strategy_start: Optional[datetime] = None
        self.switch_history: List[Dict[str, Any]] = []
        self.evaluation_callbacks: List[Callable] = []
        
        # Performance tracking
        self.strategy_trade_count: Dict[str, int] = {}
        
        logger.info("Initialized StrategySelector")
        
    def enable_auto_switching(self, enabled: bool = True):
        """Enable or disable automatic strategy switching"""
        self.auto_switch_enabled = enabled
        logger.info(f"Automatic strategy switching: {'enabled' if enabled else 'disabled'}")
        
    def evaluate_and_select(self, ohlcv_data: Any) -> Dict[str, Any]:
        """
        Evaluate current conditions and select optimal strategy
        
        Args:
            ohlcv_data: Market OHLCV data
            
        Returns:
            Selection result with recommendation
        """
        # Get available strategies
        available_strategies = self.strategy_manager.get_available_strategies()
        
        # Get recommendation
        recommendation = self.recommender.recommend_strategy(
            ohlcv_data, available_strategies
        )
        
        # Current strategy
        current_strategy = self.strategy_manager.active_strategy
        
        # Determine if switch is needed
        should_switch = False
        switch_reason = None
        
        if self.auto_switch_enabled and current_strategy:
            should_switch, switch_reason = self._should_switch_strategy(
                current_strategy, recommendation
            )
            
        # Prepare result
        result = {
            'timestamp': datetime.now(),
            'current_strategy': current_strategy,
            'recommended_strategy': recommendation['recommended_strategy'],
            'should_switch': should_switch,
            'switch_reason': switch_reason,
            'recommendation': recommendation,
            'can_switch': self._can_switch_now(current_strategy)
        }
        
        # Execute switch if needed
        if should_switch and result['can_switch']:
            new_strategy = recommendation['recommended_strategy']
            self._execute_strategy_switch(current_strategy, new_strategy, recommendation)
            result['switched'] = True
            result['new_strategy'] = new_strategy
        else:
            result['switched'] = False
            
        # Notify callbacks
        for callback in self.evaluation_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in evaluation callback: {e}")
                
        return result
        
    def _should_switch_strategy(self, current_strategy: str, 
                              recommendation: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Determine if strategy switch is warranted"""
        recommended_strategy = recommendation['recommended_strategy']
        
        # Don't switch to same strategy
        if current_strategy == recommended_strategy:
            return False, None
            
        # Check confidence threshold
        if recommendation['confidence'] < self.confidence_threshold:
            return False, "Low confidence"
            
        # Check if significant improvement
        current_score = recommendation['scores'].get(current_strategy, {}).get('score', 0)
        recommended_score = recommendation['scores'].get(recommended_strategy, {}).get('score', 0)
        
        if recommended_score - current_score < self.improvement_threshold:
            return False, "Insufficient improvement"
            
        # Check if current strategy is failing
        current_metrics = self.performance_evaluator.strategy_metrics.get(current_strategy)
        if current_metrics and current_metrics.consecutive_losses >= 3:
            return True, "Consecutive losses"
            
        # Market condition changed significantly
        if recommendation['confidence_level'] == 'HIGH':
            return True, "High confidence in new conditions"
            
        return False, None
        
    def _can_switch_now(self, current_strategy: Optional[str]) -> bool:
        """Check if switch is allowed based on constraints"""
        if not current_strategy:
            return True
            
        # Check minimum time
        if self.last_switch_time:
            time_since_switch = datetime.now() - self.last_switch_time
            if time_since_switch < self.min_time_before_switch:
                return False
                
        # Check minimum trades
        trade_count = self.strategy_trade_count.get(current_strategy, 0)
        if trade_count < self.min_trades_before_switch:
            return False
            
        # Check if position is open
        current_strategy_obj = self.strategy_manager.get_strategy(current_strategy)
        if current_strategy_obj and current_strategy_obj.position:
            return False  # Don't switch with open position
            
        return True
        
    def _execute_strategy_switch(self, old_strategy: str, new_strategy: str, 
                               recommendation: Dict[str, Any]):
        """Execute strategy switch"""
        logger.info(f"Switching strategy: {old_strategy} -> {new_strategy}")
        
        # Record switch
        switch_record = {
            'timestamp': datetime.now(),
            'from_strategy': old_strategy,
            'to_strategy': new_strategy,
            'reason': recommendation['reasoning'],
            'confidence': recommendation['confidence'],
            'market_condition': recommendation['market_condition']
        }
        
        self.switch_history.append(switch_record)
        
        # Perform switch
        self.strategy_manager.set_active_strategy(new_strategy)
        
        # Update tracking
        self.last_switch_time = datetime.now()
        self.current_strategy_start = datetime.now()
        self.strategy_trade_count[new_strategy] = 0
        
        logger.info(f"Strategy switch completed: now using {new_strategy}")
        
    def record_trade(self, strategy_name: str):
        """Record a trade for tracking minimum trades"""
        self.strategy_trade_count[strategy_name] = \
            self.strategy_trade_count.get(strategy_name, 0) + 1
            
    def get_switch_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent strategy switch history"""
        return self.switch_history[-limit:]
        
    def get_selector_stats(self) -> Dict[str, Any]:
        """Get strategy selector statistics"""
        total_switches = len(self.switch_history)
        
        # Calculate switch frequency
        if total_switches > 1:
            first_switch = self.switch_history[0]['timestamp']
            last_switch = self.switch_history[-1]['timestamp']
            time_span = (last_switch - first_switch).total_seconds() / 3600  # hours
            switch_frequency = total_switches / time_span if time_span > 0 else 0
        else:
            switch_frequency = 0
            
        # Strategy usage
        strategy_usage = {}
        for switch in self.switch_history:
            strategy = switch['to_strategy']
            strategy_usage[strategy] = strategy_usage.get(strategy, 0) + 1
            
        return {
            'auto_switch_enabled': self.auto_switch_enabled,
            'total_switches': total_switches,
            'switch_frequency_per_hour': switch_frequency,
            'current_strategy': self.strategy_manager.active_strategy,
            'time_on_current': (
                (datetime.now() - self.current_strategy_start).total_seconds() / 3600
                if self.current_strategy_start else 0
            ),
            'strategy_usage': strategy_usage,
            'last_switch': self.last_switch_time.isoformat() if self.last_switch_time else None
        }
        
    def subscribe_evaluation(self, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe to strategy evaluation events"""
        self.evaluation_callbacks.append(callback)
        
    def manual_override(self, strategy_name: str, reason: str = "Manual override"):
        """Manually override strategy selection"""
        current = self.strategy_manager.active_strategy
        
        if current == strategy_name:
            logger.info(f"Strategy {strategy_name} already active")
            return
            
        # Record manual switch
        switch_record = {
            'timestamp': datetime.now(),
            'from_strategy': current,
            'to_strategy': strategy_name,
            'reason': [reason],
            'confidence': 1.0,
            'market_condition': 'MANUAL',
            'manual': True
        }
        
        self.switch_history.append(switch_record)
        
        # Execute switch
        self.strategy_manager.set_active_strategy(strategy_name)
        self.last_switch_time = datetime.now()
        self.current_strategy_start = datetime.now()
        self.strategy_trade_count[strategy_name] = 0
        
        logger.info(f"Manual strategy override: {current} -> {strategy_name}")
        
    async def start_auto_selection(self, interval: int = 300):
        """
        Start automatic strategy selection loop
        
        Args:
            interval: Evaluation interval in seconds (default 5 minutes)
        """
        logger.info(f"Starting auto strategy selection (interval: {interval}s)")
        
        while self.auto_switch_enabled:
            try:
                # Note: In production, you'd get real OHLCV data here
                # For now, this is a placeholder
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in auto selection loop: {e}")
                await asyncio.sleep(interval)