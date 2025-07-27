# Trading strategies module for AutoCoin
from .base import Strategy, Signal, Position
from .breakout import BreakoutStrategy
from .scalping import ScalpingStrategy
from .trend import TrendFollowingStrategy
from .factory import StrategyFactory, StrategyManager

__all__ = [
    'Strategy',
    'Signal',
    'Position',
    'BreakoutStrategy',
    'ScalpingStrategy',
    'TrendFollowingStrategy',
    'StrategyFactory',
    'StrategyManager'
]