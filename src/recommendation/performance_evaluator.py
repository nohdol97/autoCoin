"""
Strategy performance evaluator for tracking and scoring strategies
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

from ..strategies import Strategy
from ..logger import get_logger

logger = get_logger('performance_evaluator')


class PerformanceMetrics:
    """Container for strategy performance metrics"""
    
    def __init__(self):
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.sharpe_ratio = 0.0
        self.win_rate = 0.0
        self.avg_win = 0.0
        self.avg_loss = 0.0
        self.profit_factor = 0.0
        self.recovery_factor = 0.0
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.max_consecutive_wins = 0
        self.max_consecutive_losses = 0
        self.last_update = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'total_pnl': self.total_pnl,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'win_rate': self.win_rate,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'profit_factor': self.profit_factor,
            'recovery_factor': self.recovery_factor,
            'consecutive_wins': self.consecutive_wins,
            'consecutive_losses': self.consecutive_losses,
            'max_consecutive_wins': self.max_consecutive_wins,
            'max_consecutive_losses': self.max_consecutive_losses,
            'last_update': self.last_update.isoformat()
        }


class PerformanceEvaluator:
    """Evaluates and tracks strategy performance"""
    
    def __init__(self):
        # Performance tracking by strategy
        self.strategy_metrics: Dict[str, PerformanceMetrics] = {}
        self.strategy_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Market condition performance
        self.condition_performance: Dict[str, Dict[str, PerformanceMetrics]] = defaultdict(dict)
        
        # Time-based performance
        self.hourly_performance: Dict[str, List[float]] = defaultdict(list)
        self.daily_performance: Dict[str, List[float]] = defaultdict(list)
        
        logger.info("Initialized PerformanceEvaluator")
        
    def update_performance(self, strategy_name: str, position_data: Dict[str, Any], 
                         market_condition: Optional[str] = None):
        """
        Update performance metrics for a strategy
        
        Args:
            strategy_name: Name of the strategy
            position_data: Closed position data
            market_condition: Market condition during trade
        """
        # Initialize metrics if needed
        if strategy_name not in self.strategy_metrics:
            self.strategy_metrics[strategy_name] = PerformanceMetrics()
            
        metrics = self.strategy_metrics[strategy_name]
        pnl = position_data.get('pnl', 0)
        
        # Update basic metrics
        metrics.total_trades += 1
        metrics.total_pnl += pnl
        
        if pnl > 0:
            metrics.winning_trades += 1
            metrics.consecutive_wins += 1
            metrics.consecutive_losses = 0
            metrics.max_consecutive_wins = max(metrics.max_consecutive_wins, metrics.consecutive_wins)
        else:
            metrics.losing_trades += 1
            metrics.consecutive_losses += 1
            metrics.consecutive_wins = 0
            metrics.max_consecutive_losses = max(metrics.max_consecutive_losses, metrics.consecutive_losses)
            
        # Store history
        self.strategy_history[strategy_name].append({
            'timestamp': datetime.now(),
            'pnl': pnl,
            'pnl_percentage': position_data.get('pnl_percentage', 0),
            'duration': position_data.get('duration', 0),
            'market_condition': market_condition
        })
        
        # Update market condition performance
        if market_condition:
            if market_condition not in self.condition_performance[strategy_name]:
                self.condition_performance[strategy_name][market_condition] = PerformanceMetrics()
            
            condition_metrics = self.condition_performance[strategy_name][market_condition]
            condition_metrics.total_trades += 1
            condition_metrics.total_pnl += pnl
            if pnl > 0:
                condition_metrics.winning_trades += 1
            else:
                condition_metrics.losing_trades += 1
                
        # Recalculate derived metrics
        self._recalculate_metrics(strategy_name)
        
        logger.info(f"Updated performance for {strategy_name}: "
                   f"Trade #{metrics.total_trades}, PnL: ${pnl:.2f}")
        
    def _recalculate_metrics(self, strategy_name: str):
        """Recalculate derived metrics"""
        metrics = self.strategy_metrics[strategy_name]
        history = self.strategy_history[strategy_name]
        
        if metrics.total_trades == 0:
            return
            
        # Win rate
        metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100
        
        # Average win/loss
        wins = [h['pnl'] for h in history if h['pnl'] > 0]
        losses = [h['pnl'] for h in history if h['pnl'] < 0]
        
        metrics.avg_win = np.mean(wins) if wins else 0
        metrics.avg_loss = abs(np.mean(losses)) if losses else 0
        
        # Profit factor
        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 0
        metrics.profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Maximum drawdown
        cumulative_pnl = np.cumsum([h['pnl'] for h in history])
        if len(cumulative_pnl) > 0:
            running_max = np.maximum.accumulate(cumulative_pnl)
            drawdowns = running_max - cumulative_pnl
            metrics.max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0
            
        # Sharpe ratio (simplified daily)
        if len(history) > 1:
            returns = [h['pnl_percentage'] for h in history]
            if np.std(returns) > 0:
                metrics.sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252)
            else:
                metrics.sharpe_ratio = 0
                
        # Recovery factor
        if metrics.max_drawdown > 0:
            metrics.recovery_factor = metrics.total_pnl / metrics.max_drawdown
            
        metrics.last_update = datetime.now()
        
    def get_strategy_score(self, strategy_name: str, 
                          market_condition: Optional[str] = None) -> float:
        """
        Calculate a composite score for strategy performance
        
        Args:
            strategy_name: Name of the strategy
            market_condition: Optional market condition filter
            
        Returns:
            Performance score (0-100)
        """
        if strategy_name not in self.strategy_metrics:
            return 50.0  # Default neutral score
            
        # Use market-specific metrics if provided
        if market_condition and market_condition in self.condition_performance[strategy_name]:
            metrics = self.condition_performance[strategy_name][market_condition]
        else:
            metrics = self.strategy_metrics[strategy_name]
            
        if metrics.total_trades < 5:
            return 50.0  # Not enough data
            
        # Score components (weighted)
        score_components = {
            'win_rate': (metrics.win_rate / 100) * 25,  # Max 25 points
            'profit_factor': min(metrics.profit_factor / 2, 1) * 20,  # Max 20 points
            'sharpe_ratio': min(max(metrics.sharpe_ratio / 2, 0), 1) * 15,  # Max 15 points
            'consistency': (1 - min(metrics.max_consecutive_losses / 5, 1)) * 15,  # Max 15 points
            'drawdown': (1 - min(metrics.max_drawdown / 1000, 1)) * 15,  # Max 15 points
            'recency': self._get_recency_score(strategy_name) * 10  # Max 10 points
        }
        
        total_score = sum(score_components.values())
        
        logger.debug(f"Strategy {strategy_name} score: {total_score:.2f} "
                    f"(components: {score_components})")
        
        return min(max(total_score, 0), 100)
        
    def _get_recency_score(self, strategy_name: str) -> float:
        """Get score based on recent performance"""
        history = self.strategy_history[strategy_name]
        if len(history) < 3:
            return 0.5
            
        # Look at last 5 trades
        recent_trades = history[-5:]
        recent_wins = sum(1 for t in recent_trades if t['pnl'] > 0)
        
        return recent_wins / len(recent_trades)
        
    def get_best_strategy_for_condition(self, market_condition: str, 
                                      available_strategies: List[str]) -> Optional[str]:
        """
        Get the best performing strategy for a market condition
        
        Args:
            market_condition: Current market condition
            available_strategies: List of available strategy names
            
        Returns:
            Best strategy name or None
        """
        best_strategy = None
        best_score = 0
        
        for strategy in available_strategies:
            score = self.get_strategy_score(strategy, market_condition)
            if score > best_score:
                best_score = score
                best_strategy = strategy
                
        logger.info(f"Best strategy for {market_condition}: "
                   f"{best_strategy} (score: {best_score:.2f})")
        
        return best_strategy
        
    def get_performance_summary(self, strategy_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance summary
        
        Args:
            strategy_name: Optional specific strategy, otherwise all strategies
            
        Returns:
            Performance summary
        """
        if strategy_name:
            if strategy_name not in self.strategy_metrics:
                return {}
                
            metrics = self.strategy_metrics[strategy_name]
            return {
                'strategy': strategy_name,
                'metrics': metrics.to_dict(),
                'score': self.get_strategy_score(strategy_name),
                'market_conditions': {
                    condition: self.condition_performance[strategy_name][condition].to_dict()
                    for condition in self.condition_performance[strategy_name]
                }
            }
        else:
            # All strategies summary
            summary = {}
            for name, metrics in self.strategy_metrics.items():
                summary[name] = {
                    'metrics': metrics.to_dict(),
                    'score': self.get_strategy_score(name)
                }
            return summary
            
    def reset_strategy_performance(self, strategy_name: str):
        """Reset performance data for a strategy"""
        if strategy_name in self.strategy_metrics:
            self.strategy_metrics[strategy_name] = PerformanceMetrics()
            self.strategy_history[strategy_name].clear()
            self.condition_performance[strategy_name].clear()
            logger.info(f"Reset performance data for {strategy_name}")