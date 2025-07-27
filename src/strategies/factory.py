"""
Strategy Factory for creating and managing trading strategies
"""

from typing import Dict, Any, Optional, List
from .base import Strategy
from .breakout import BreakoutStrategy
from .scalping import ScalpingStrategy
from .trend import TrendFollowingStrategy
from ..logger import get_logger

logger = get_logger('strategy_factory')


class StrategyFactory:
    """Factory class for creating trading strategies"""
    
    # Available strategies
    STRATEGIES = {
        'breakout': BreakoutStrategy,
        'scalping': ScalpingStrategy,
        'trend': TrendFollowingStrategy
    }
    
    @classmethod
    def create_strategy(cls, name: str, config: Dict[str, Any]) -> Strategy:
        """
        Create a strategy instance
        
        Args:
            name: Strategy name
            config: Strategy configuration
            
        Returns:
            Strategy instance
            
        Raises:
            ValueError: If strategy name is unknown
        """
        if name not in cls.STRATEGIES:
            raise ValueError(f"Unknown strategy: {name}. "
                           f"Available: {list(cls.STRATEGIES.keys())}")
            
        strategy_class = cls.STRATEGIES[name]
        strategy = strategy_class(config)
        
        logger.info(f"Created {name} strategy")
        return strategy
        
    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Get list of available strategy names"""
        return list(cls.STRATEGIES.keys())
        
    @classmethod
    def get_strategy_info(cls, name: str) -> Dict[str, Any]:
        """
        Get information about a strategy
        
        Args:
            name: Strategy name
            
        Returns:
            Strategy information
        """
        if name not in cls.STRATEGIES:
            raise ValueError(f"Unknown strategy: {name}")
            
        info = {
            'name': name,
            'class': cls.STRATEGIES[name].__name__,
            'description': cls.STRATEGIES[name].__doc__.strip()
        }
        
        # Add default parameters based on strategy
        if name == 'breakout':
            info['parameters'] = {
                'lookback_buy': 20,
                'lookback_sell': 10,
                'stop_loss': 2.0,
                'take_profit': 5.0
            }
        elif name == 'scalping':
            info['parameters'] = {
                'rsi_period': 14,
                'rsi_oversold': 30,
                'rsi_overbought': 70,
                'bb_period': 20,
                'bb_std': 2,
                'stop_loss': 0.5,
                'take_profit': 1.0
            }
        elif name == 'trend':
            info['parameters'] = {
                'ema_fast': 12,
                'ema_slow': 26,
                'trailing_stop': 3.0,
                'stop_loss': 3.0,
                'take_profit': 10.0
            }
            
        return info


class StrategyManager:
    """Manager for handling multiple strategies"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.strategies: Dict[str, Strategy] = {}
        self.active_strategy: Optional[str] = None
        
        logger.info("Initialized StrategyManager")
        
    def load_strategy(self, name: str) -> Strategy:
        """
        Load a strategy
        
        Args:
            name: Strategy name
            
        Returns:
            Strategy instance
        """
        if name in self.strategies:
            logger.info(f"Strategy {name} already loaded")
            return self.strategies[name]
            
        # Get strategy config from main config
        strategy_config = self.config.get('strategies', {}).get(name, {})
        
        # Create strategy
        strategy = StrategyFactory.create_strategy(name, strategy_config)
        self.strategies[name] = strategy
        
        logger.info(f"Loaded strategy: {name}")
        return strategy
        
    def set_active_strategy(self, name: str) -> Strategy:
        """
        Set the active strategy
        
        Args:
            name: Strategy name
            
        Returns:
            Active strategy instance
        """
        if name not in self.strategies:
            self.load_strategy(name)
            
        self.active_strategy = name
        logger.info(f"Set active strategy: {name}")
        
        return self.strategies[name]
        
    def get_active_strategy(self) -> Optional[Strategy]:
        """Get the currently active strategy"""
        if not self.active_strategy:
            return None
            
        return self.strategies.get(self.active_strategy)
        
    def get_strategy(self, name: str) -> Optional[Strategy]:
        """Get a specific strategy by name"""
        return self.strategies.get(name)
        
    def reset_strategy(self, name: str):
        """Reset a strategy's state"""
        if name in self.strategies:
            self.strategies[name].reset()
            logger.info(f"Reset strategy: {name}")
            
    def reset_all_strategies(self):
        """Reset all strategies"""
        for name, strategy in self.strategies.items():
            strategy.reset()
        logger.info("Reset all strategies")
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all loaded strategies"""
        summary = {}
        
        for name, strategy in self.strategies.items():
            summary[name] = strategy.get_performance_stats()
            
        return summary
        
    def get_available_strategies(self) -> List[str]:
        """Get list of available strategies"""
        return StrategyFactory.get_available_strategies()