"""
Strategy recommendation system that combines market analysis and performance evaluation
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np

from .market_analyzer import MarketAnalyzer, MarketCondition
from .performance_evaluator import PerformanceEvaluator
from ..logger import get_logger

logger = get_logger('strategy_recommender')


class StrategyRecommender:
    """Recommends optimal trading strategies based on market conditions and performance"""
    
    def __init__(self, market_analyzer: MarketAnalyzer, 
                 performance_evaluator: PerformanceEvaluator):
        self.market_analyzer = market_analyzer
        self.performance_evaluator = performance_evaluator
        
        # Strategy suitability matrix (strategy -> market conditions)
        self.suitability_matrix = {
            'breakout': {
                MarketCondition.BREAKOUT: 0.9,
                MarketCondition.TRENDING_UP: 0.8,
                MarketCondition.TRENDING_DOWN: 0.7,
                MarketCondition.VOLATILE: 0.6,
                MarketCondition.RANGING: 0.3,
                MarketCondition.CONSOLIDATING: 0.4
            },
            'scalping': {
                MarketCondition.RANGING: 0.9,
                MarketCondition.VOLATILE: 0.8,
                MarketCondition.CONSOLIDATING: 0.7,
                MarketCondition.TRENDING_UP: 0.4,
                MarketCondition.TRENDING_DOWN: 0.4,
                MarketCondition.BREAKOUT: 0.3
            },
            'trend': {
                MarketCondition.TRENDING_UP: 0.95,
                MarketCondition.TRENDING_DOWN: 0.9,
                MarketCondition.BREAKOUT: 0.7,
                MarketCondition.VOLATILE: 0.5,
                MarketCondition.RANGING: 0.2,
                MarketCondition.CONSOLIDATING: 0.2
            }
        }
        
        # Confidence thresholds
        self.min_confidence = 0.6
        self.high_confidence = 0.8
        
        # Recommendation history
        self.recommendation_history: List[Dict[str, Any]] = []
        self.last_recommendation_time: Optional[datetime] = None
        
        logger.info("Initialized StrategyRecommender")
        
    def recommend_strategy(self, ohlcv_data: Any, 
                         available_strategies: List[str]) -> Dict[str, Any]:
        """
        Recommend the best strategy for current conditions
        
        Args:
            ohlcv_data: Market OHLCV data
            available_strategies: List of available strategy names
            
        Returns:
            Recommendation with confidence and reasoning
        """
        try:
            # Analyze current market
            market_analysis = self.market_analyzer.analyze_market(ohlcv_data)
            if not market_analysis:
                logger.warning("Failed to analyze market")
                return self._default_recommendation(available_strategies)
                
            market_condition = market_analysis['market_condition']
            
            # Calculate scores for each strategy
            strategy_scores = {}
            for strategy in available_strategies:
                score, components = self._calculate_strategy_score(
                    strategy, market_condition, market_analysis
                )
                strategy_scores[strategy] = {
                    'score': score,
                    'components': components
                }
                
            # Select best strategy
            best_strategy = max(strategy_scores.keys(), 
                              key=lambda s: strategy_scores[s]['score'])
            best_score = strategy_scores[best_strategy]['score']
            
            # Calculate confidence
            confidence = self._calculate_confidence(
                best_score, strategy_scores, market_analysis
            )
            
            # Generate reasoning
            reasoning = self._generate_reasoning(
                best_strategy, market_condition, 
                strategy_scores[best_strategy]['components'],
                market_analysis
            )
            
            # Create recommendation
            recommendation = {
                'timestamp': datetime.now(),
                'recommended_strategy': best_strategy,
                'confidence': confidence,
                'confidence_level': self._get_confidence_level(confidence),
                'market_condition': market_condition.value,
                'reasoning': reasoning,
                'scores': strategy_scores,
                'market_analysis': {
                    'trend': market_analysis['trend']['direction'],
                    'volatility': market_analysis['volatility']['level'],
                    'momentum': market_analysis['momentum']['rsi_state']
                },
                'alternative_strategies': self._get_alternatives(
                    strategy_scores, best_strategy
                )
            }
            
            # Store in history
            self.recommendation_history.append(recommendation)
            self.last_recommendation_time = datetime.now()
            
            logger.info(f"Recommended: {best_strategy} "
                       f"(confidence: {confidence:.2f}, condition: {market_condition.value})")
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error generating recommendation: {e}")
            return self._default_recommendation(available_strategies)
            
    def _calculate_strategy_score(self, strategy: str, 
                                market_condition: MarketCondition,
                                market_analysis: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """Calculate comprehensive score for a strategy"""
        components = {}
        
        # 1. Market condition suitability (40%)
        suitability = self.suitability_matrix.get(strategy, {}).get(market_condition, 0.5)
        components['suitability'] = suitability * 0.4
        
        # 2. Historical performance (30%)
        performance_score = self.performance_evaluator.get_strategy_score(
            strategy, market_condition.value
        ) / 100
        components['performance'] = performance_score * 0.3
        
        # 3. Current market alignment (20%)
        alignment_score = self._calculate_market_alignment(strategy, market_analysis)
        components['alignment'] = alignment_score * 0.2
        
        # 4. Risk assessment (10%)
        risk_score = self._calculate_risk_score(strategy, market_analysis)
        components['risk'] = risk_score * 0.1
        
        total_score = sum(components.values())
        
        return total_score, components
        
    def _calculate_market_alignment(self, strategy: str, 
                                  market_analysis: Dict[str, Any]) -> float:
        """Calculate how well strategy aligns with current market"""
        alignment = 0.5  # Default neutral
        
        trend = market_analysis['trend']
        volatility = market_analysis['volatility']
        momentum = market_analysis['momentum']
        
        if strategy == 'breakout':
            # Breakout likes strong trends and increasing volatility
            if trend['strength'].value in ['STRONG', 'MODERATE']:
                alignment += 0.2
            if volatility['trend'] == 'INCREASING':
                alignment += 0.2
            if abs(momentum['rsi'] - 50) > 20:  # Strong momentum
                alignment += 0.1
                
        elif strategy == 'scalping':
            # Scalping likes ranging markets with normal volatility
            if not trend['is_trending']:
                alignment += 0.3
            if volatility['level'] == 'NORMAL':
                alignment += 0.2
            if 40 < momentum['rsi'] < 60:  # Neutral RSI
                alignment += 0.1
                
        elif strategy == 'trend':
            # Trend following likes strong trends with aligned MAs
            if trend['is_trending'] and trend['ma_aligned']:
                alignment += 0.3
            if trend['strength'].value == 'STRONG':
                alignment += 0.2
            if momentum['macd_trend'] == 'BULLISH' and trend['direction'] == 'UP':
                alignment += 0.1
                
        return min(alignment, 1.0)
        
    def _calculate_risk_score(self, strategy: str, 
                            market_analysis: Dict[str, Any]) -> float:
        """Calculate risk-adjusted score"""
        risk_score = 0.7  # Default moderate risk acceptance
        
        volatility = market_analysis['volatility']
        
        # Adjust based on volatility
        if volatility['level'] == 'HIGH':
            if strategy == 'scalping':
                risk_score = 0.5  # Higher risk for scalping in high volatility
            elif strategy == 'trend':
                risk_score = 0.8  # Trend following can handle volatility
        elif volatility['level'] == 'LOW':
            if strategy == 'breakout':
                risk_score = 0.6  # Lower opportunity in low volatility
                
        return risk_score
        
    def _calculate_confidence(self, best_score: float,
                            all_scores: Dict[str, Dict[str, Any]],
                            market_analysis: Dict[str, Any]) -> float:
        """Calculate confidence in recommendation"""
        # Base confidence from best score
        confidence = best_score
        
        # Adjust based on score differentiation
        scores = [s['score'] for s in all_scores.values()]
        if len(scores) > 1:
            score_std = np.std(scores)
            if score_std > 0.1:  # Clear winner
                confidence += 0.1
            elif score_std < 0.05:  # Too close to call
                confidence -= 0.1
                
        # Adjust based on market clarity
        if market_analysis['trend']['strength'].value == 'STRONG':
            confidence += 0.05
        elif market_analysis['trend']['strength'].value == 'NONE':
            confidence -= 0.05
            
        return min(max(confidence, 0), 1)
        
    def _get_confidence_level(self, confidence: float) -> str:
        """Convert confidence score to level"""
        if confidence >= self.high_confidence:
            return "HIGH"
        elif confidence >= self.min_confidence:
            return "MEDIUM"
        else:
            return "LOW"
            
    def _generate_reasoning(self, strategy: str, 
                          market_condition: MarketCondition,
                          score_components: Dict[str, float],
                          market_analysis: Dict[str, Any]) -> List[str]:
        """Generate human-readable reasoning"""
        reasoning = []
        
        # Market condition reasoning
        reasoning.append(
            f"Market is currently {market_condition.value.replace('_', ' ').lower()}"
        )
        
        # Strategy suitability
        suitability_score = score_components['suitability'] / 0.4
        if suitability_score > 0.8:
            reasoning.append(f"{strategy.capitalize()} strategy is highly suitable for this market")
        elif suitability_score > 0.6:
            reasoning.append(f"{strategy.capitalize()} strategy is moderately suitable")
            
        # Performance reasoning
        performance_score = score_components['performance'] / 0.3
        if performance_score > 0.7:
            reasoning.append(f"Strong historical performance in similar conditions")
        elif performance_score < 0.3:
            reasoning.append(f"Limited historical performance data available")
            
        # Market specifics
        if market_analysis['volatility']['level'] == 'HIGH':
            reasoning.append("High volatility presents both opportunity and risk")
        if market_analysis['trend']['is_trending']:
            reasoning.append(f"Clear {market_analysis['trend']['direction'].lower()} trend detected")
            
        return reasoning
        
    def _get_alternatives(self, all_scores: Dict[str, Dict[str, Any]], 
                        best_strategy: str) -> List[Dict[str, Any]]:
        """Get alternative strategy recommendations"""
        alternatives = []
        
        for strategy, data in all_scores.items():
            if strategy != best_strategy:
                alternatives.append({
                    'strategy': strategy,
                    'score': data['score'],
                    'gap': all_scores[best_strategy]['score'] - data['score']
                })
                
        # Sort by score
        alternatives.sort(key=lambda x: x['score'], reverse=True)
        
        return alternatives[:2]  # Top 2 alternatives
        
    def _default_recommendation(self, available_strategies: List[str]) -> Dict[str, Any]:
        """Default recommendation when analysis fails"""
        return {
            'timestamp': datetime.now(),
            'recommended_strategy': available_strategies[0] if available_strategies else None,
            'confidence': 0.5,
            'confidence_level': 'LOW',
            'market_condition': 'UNKNOWN',
            'reasoning': ['Unable to analyze market conditions', 
                         'Using default strategy selection'],
            'scores': {},
            'market_analysis': {},
            'alternative_strategies': []
        }
        
    def get_recommendation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent recommendation history"""
        return self.recommendation_history[-limit:]
        
    def should_switch_strategy(self, current_strategy: str, 
                             min_improvement: float = 0.1) -> Tuple[bool, Optional[str]]:
        """
        Determine if strategy should be switched
        
        Args:
            current_strategy: Currently active strategy
            min_improvement: Minimum score improvement required
            
        Returns:
            (should_switch, new_strategy)
        """
        if not self.recommendation_history:
            return False, None
            
        latest = self.recommendation_history[-1]
        recommended = latest['recommended_strategy']
        
        if recommended == current_strategy:
            return False, None
            
        # Check if improvement is significant
        current_score = latest['scores'].get(current_strategy, {}).get('score', 0)
        recommended_score = latest['scores'].get(recommended, {}).get('score', 0)
        
        if recommended_score - current_score > min_improvement:
            logger.info(f"Strategy switch recommended: {current_strategy} -> {recommended} "
                       f"(improvement: {recommended_score - current_score:.3f})")
            return True, recommended
            
        return False, None