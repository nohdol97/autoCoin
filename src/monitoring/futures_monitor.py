"""
Futures Trading Monitor
Real-time monitoring and alerting for futures positions
"""
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
from dataclasses import asdict

from ..exchange.binance_futures_client import BinanceFuturesClient
from ..trading.futures_position_manager import FuturesPositionManager
from ..trading.futures_types import RiskMetrics, FuturesPosition
from ..utils.risk_manager import RiskManager
from ..logger import get_logger
from .prometheus_metrics import PrometheusMetrics

logger = get_logger('futures_monitor')


class FuturesMonitor:
    """Comprehensive monitoring for futures trading"""
    
    def __init__(self, futures_client: BinanceFuturesClient, 
                 position_manager: FuturesPositionManager,
                 prometheus_metrics: Optional[PrometheusMetrics] = None):
        self.futures_client = futures_client
        self.position_manager = position_manager
        self.prometheus_metrics = prometheus_metrics
        
        # Monitoring configuration
        self.position_update_interval = 5  # seconds
        self.risk_check_interval = 30  # seconds
        self.funding_check_interval = 3600  # 1 hour
        self.performance_update_interval = 300  # 5 minutes
        
        # Alert thresholds
        self.liquidation_warning_distance = 0.1  # 10% from liquidation
        self.margin_usage_warning = 0.8  # 80% margin usage
        self.daily_loss_limit = -0.05  # -5% daily loss
        self.position_size_limit = 0.5  # 50% of capital per position
        
        # State tracking
        self.alerts_sent: Dict[str, datetime] = {}
        self.alert_cooldown = timedelta(minutes=15)
        self.daily_pnl_start = 0
        self.performance_history: List[Dict] = []
        
        # Monitoring tasks
        self._monitoring_tasks: List[asyncio.Task] = []
        self.is_monitoring = False
        
        logger.info("Futures monitor initialized")
        
    async def start_monitoring(self):
        """Start all monitoring tasks"""
        if self.is_monitoring:
            logger.warning("Monitoring already running")
            return
            
        self.is_monitoring = True
        logger.info("Starting futures monitoring...")
        
        # Initialize daily PnL tracking
        await self._initialize_daily_tracking()
        
        # Create monitoring tasks
        self._monitoring_tasks = [
            asyncio.create_task(self._position_monitoring_loop()),
            asyncio.create_task(self._risk_monitoring_loop()),
            asyncio.create_task(self._funding_monitoring_loop()),
            asyncio.create_task(self._performance_monitoring_loop()),
            asyncio.create_task(self._alert_monitoring_loop())
        ]
        
        logger.info("Futures monitoring started")
        
    async def stop_monitoring(self):
        """Stop all monitoring tasks"""
        self.is_monitoring = False
        
        # Cancel all tasks
        for task in self._monitoring_tasks:
            if not task.done():
                task.cancel()
                
        # Wait for tasks to complete
        await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        self._monitoring_tasks.clear()
        
        logger.info("Futures monitoring stopped")
        
    async def _position_monitoring_loop(self):
        """Monitor position changes and updates"""
        logger.info("Position monitoring started")
        
        while self.is_monitoring:
            try:
                # Update positions
                await self.position_manager.update_positions()
                
                # Export metrics if available
                if self.prometheus_metrics:
                    for symbol, position in self.position_manager.positions.items():
                        self._export_position_metrics(position)
                        
                # Check for position-specific alerts
                await self._check_position_alerts()
                
            except Exception as e:
                logger.error(f"Position monitoring error: {e}")
                
            await asyncio.sleep(self.position_update_interval)
            
    async def _risk_monitoring_loop(self):
        """Monitor overall risk metrics"""
        logger.info("Risk monitoring started")
        
        while self.is_monitoring:
            try:
                # Get risk metrics
                risk_metrics = await self.position_manager.get_risk_metrics()
                
                # Export metrics
                if self.prometheus_metrics:
                    self._export_risk_metrics(risk_metrics)
                    
                # Check risk alerts
                await self._check_risk_alerts(risk_metrics)
                
                # Check liquidation risks
                at_risk = await self.position_manager.check_liquidation_risk()
                await self._check_liquidation_alerts(at_risk)
                
            except Exception as e:
                logger.error(f"Risk monitoring error: {e}")
                
            await asyncio.sleep(self.risk_check_interval)
            
    async def _funding_monitoring_loop(self):
        """Monitor funding rates"""
        logger.info("Funding monitoring started")
        
        while self.is_monitoring:
            try:
                # Check funding for all positions
                for symbol in self.position_manager.positions:
                    funding = await self.position_manager.get_funding_rate(symbol)
                    
                    if funding:
                        # Export metrics
                        if self.prometheus_metrics:
                            self.prometheus_metrics.funding_rate.labels(
                                symbol=symbol
                            ).set(funding.rate)
                            
                        # Check for high funding
                        await self._check_funding_alerts(symbol, funding)
                        
            except Exception as e:
                logger.error(f"Funding monitoring error: {e}")
                
            await asyncio.sleep(self.funding_check_interval)
            
    async def _performance_monitoring_loop(self):
        """Monitor trading performance"""
        logger.info("Performance monitoring started")
        
        while self.is_monitoring:
            try:
                # Calculate performance metrics
                performance = await self._calculate_performance()
                
                # Store in history
                self.performance_history.append(performance)
                if len(self.performance_history) > 288:  # Keep 24 hours at 5min intervals
                    self.performance_history.pop(0)
                    
                # Export metrics
                if self.prometheus_metrics:
                    self._export_performance_metrics(performance)
                    
                # Check performance alerts
                await self._check_performance_alerts(performance)
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                
            await asyncio.sleep(self.performance_update_interval)
            
    async def _alert_monitoring_loop(self):
        """Monitor and manage alerts"""
        logger.info("Alert monitoring started")
        
        while self.is_monitoring:
            try:
                # Clean up old alerts
                current_time = datetime.now()
                expired_alerts = [
                    alert_id for alert_id, sent_time in self.alerts_sent.items()
                    if current_time - sent_time > self.alert_cooldown
                ]
                
                for alert_id in expired_alerts:
                    del self.alerts_sent[alert_id]
                    
            except Exception as e:
                logger.error(f"Alert monitoring error: {e}")
                
            await asyncio.sleep(60)  # Check every minute
            
    async def _initialize_daily_tracking(self):
        """Initialize daily PnL tracking"""
        try:
            # Get current total PnL
            position_summary = self.position_manager.get_position_summary()
            self.daily_pnl_start = position_summary['total_pnl']
            
        except Exception as e:
            logger.error(f"Failed to initialize daily tracking: {e}")
            self.daily_pnl_start = 0
            
    async def _calculate_performance(self) -> Dict:
        """Calculate current performance metrics"""
        try:
            # Get position summary
            position_summary = self.position_manager.get_position_summary()
            
            # Get risk metrics
            risk_metrics = await self.position_manager.get_risk_metrics()
            
            # Calculate daily PnL
            current_total_pnl = position_summary['total_pnl']
            daily_pnl = current_total_pnl - self.daily_pnl_start
            
            # Calculate win rate from history
            if self.performance_history:
                profitable_periods = sum(
                    1 for p in self.performance_history[-12:]  # Last hour
                    if p['period_pnl'] > 0
                )
                win_rate = profitable_periods / min(len(self.performance_history), 12)
            else:
                win_rate = 0
                
            return {
                'timestamp': datetime.now(),
                'total_pnl': current_total_pnl,
                'daily_pnl': daily_pnl,
                'period_pnl': current_total_pnl - (
                    self.performance_history[-1]['total_pnl'] 
                    if self.performance_history else 0
                ),
                'positions_count': position_summary['count'],
                'total_notional': position_summary['total_notional'],
                'margin_usage': risk_metrics.margin_usage_percentage,
                'win_rate': win_rate,
                'current_leverage': risk_metrics.current_leverage
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate performance: {e}")
            return {
                'timestamp': datetime.now(),
                'total_pnl': 0,
                'daily_pnl': 0,
                'period_pnl': 0,
                'positions_count': 0,
                'total_notional': 0,
                'margin_usage': 0,
                'win_rate': 0,
                'current_leverage': 0
            }
            
    async def _check_position_alerts(self):
        """Check for position-specific alerts"""
        for symbol, position in self.position_manager.positions.items():
            # Large position alert
            if position.notional > self.position_size_limit * position.margin:
                await self._send_alert(
                    f"large_position_{symbol}",
                    f"Large position alert for {symbol}: "
                    f"{position.notional / position.margin:.1f}x of margin"
                )
                
            # Large loss alert
            if position.pnl_percentage < -10:  # -10% loss
                await self._send_alert(
                    f"large_loss_{symbol}",
                    f"Large loss alert for {symbol}: {position.pnl_percentage:.2f}%"
                )
                
    async def _check_risk_alerts(self, risk_metrics: RiskMetrics):
        """Check for risk-related alerts"""
        # Overleveraged alert
        if risk_metrics.is_overleveraged:
            await self._send_alert(
                "overleveraged",
                f"Account overleveraged! Margin level: {risk_metrics.margin_level:.1f}%"
            )
            
        # High margin usage alert
        if risk_metrics.margin_usage_percentage > self.margin_usage_warning * 100:
            await self._send_alert(
                "high_margin_usage",
                f"High margin usage: {risk_metrics.margin_usage_percentage:.1f}%"
            )
            
        # Too many positions alert
        if risk_metrics.positions_count > 10:
            await self._send_alert(
                "too_many_positions",
                f"Too many open positions: {risk_metrics.positions_count}"
            )
            
    async def _check_liquidation_alerts(self, at_risk: List[Dict]):
        """Check for liquidation risk alerts"""
        for position in at_risk:
            if position['distance_percentage'] < self.liquidation_warning_distance * 100:
                alert_level = "CRITICAL" if position['risk_level'] == 'HIGH' else "WARNING"
                
                await self._send_alert(
                    f"liquidation_risk_{position['symbol']}",
                    f"{alert_level}: {position['symbol']} liquidation risk - "
                    f"Distance: {position['distance_percentage']:.2f}%"
                )
                
    async def _check_funding_alerts(self, symbol: str, funding):
        """Check for funding rate alerts"""
        # High positive funding (shorts profitable)
        if funding.rate > 0.01:  # 1%
            await self._send_alert(
                f"high_funding_{symbol}",
                f"High funding rate for {symbol}: {funding.rate:.4%} "
                f"(Annual: {funding.annual_rate:.2f}%)"
            )
            
        # High negative funding (longs profitable)
        elif funding.rate < -0.01:  # -1%
            await self._send_alert(
                f"negative_funding_{symbol}",
                f"Negative funding rate for {symbol}: {funding.rate:.4%} "
                f"(Annual: {funding.annual_rate:.2f}%)"
            )
            
    async def _check_performance_alerts(self, performance: Dict):
        """Check for performance-related alerts"""
        # Daily loss limit alert
        if performance['daily_pnl'] < self.daily_loss_limit * performance.get('starting_capital', 10000):
            await self._send_alert(
                "daily_loss_limit",
                f"Daily loss limit reached: ${performance['daily_pnl']:,.2f}"
            )
            
        # Low win rate alert
        if performance['win_rate'] < 0.3 and len(self.performance_history) > 12:
            await self._send_alert(
                "low_win_rate",
                f"Low win rate: {performance['win_rate']:.1%}"
            )
            
    async def _send_alert(self, alert_id: str, message: str):
        """Send alert if not in cooldown"""
        if alert_id in self.alerts_sent:
            # Check if cooldown has passed
            if datetime.now() - self.alerts_sent[alert_id] < self.alert_cooldown:
                return
                
        # Send alert
        logger.warning(f"ALERT: {message}")
        self.alerts_sent[alert_id] = datetime.now()
        
        # Here you would integrate with notification system
        # e.g., send to Telegram, email, etc.
        
    def _export_position_metrics(self, position: FuturesPosition):
        """Export position metrics to Prometheus"""
        if not self.prometheus_metrics:
            return
            
        labels = {
            'symbol': position.symbol,
            'side': position.side.value
        }
        
        self.prometheus_metrics.futures_position_size.labels(**labels).set(
            abs(position.contracts)
        )
        self.prometheus_metrics.futures_position_pnl.labels(**labels).set(
            position.unrealized_pnl
        )
        self.prometheus_metrics.futures_position_margin.labels(**labels).set(
            position.margin
        )
        
    def _export_risk_metrics(self, risk_metrics: RiskMetrics):
        """Export risk metrics to Prometheus"""
        if not self.prometheus_metrics:
            return
            
        self.prometheus_metrics.futures_margin_level.set(risk_metrics.margin_level)
        self.prometheus_metrics.futures_margin_usage.set(risk_metrics.margin_usage_percentage)
        self.prometheus_metrics.futures_leverage.set(risk_metrics.current_leverage)
        self.prometheus_metrics.futures_positions_count.set(risk_metrics.positions_count)
        
    def _export_performance_metrics(self, performance: Dict):
        """Export performance metrics to Prometheus"""
        if not self.prometheus_metrics:
            return
            
        self.prometheus_metrics.futures_total_pnl.set(performance['total_pnl'])
        self.prometheus_metrics.futures_daily_pnl.set(performance['daily_pnl'])
        self.prometheus_metrics.futures_win_rate.set(performance['win_rate'])
        
    def get_monitoring_status(self) -> Dict:
        """Get current monitoring status"""
        return {
            'is_monitoring': self.is_monitoring,
            'active_alerts': len(self.alerts_sent),
            'positions_monitored': len(self.position_manager.positions),
            'performance_history_size': len(self.performance_history),
            'last_update': self.performance_history[-1]['timestamp'].isoformat() 
                          if self.performance_history else None
        }
        
    def get_performance_summary(self) -> Dict:
        """Get performance summary"""
        if not self.performance_history:
            return {
                'total_pnl': 0,
                'daily_pnl': 0,
                'hourly_pnl': 0,
                'win_rate': 0,
                'avg_leverage': 0,
                'max_drawdown': 0
            }
            
        latest = self.performance_history[-1]
        hourly_pnl = sum(p['period_pnl'] for p in self.performance_history[-12:])
        
        # Calculate max drawdown
        peak = 0
        max_drawdown = 0
        for p in self.performance_history:
            if p['total_pnl'] > peak:
                peak = p['total_pnl']
            drawdown = (peak - p['total_pnl']) / abs(peak) if peak != 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
            
        return {
            'total_pnl': latest['total_pnl'],
            'daily_pnl': latest['daily_pnl'],
            'hourly_pnl': hourly_pnl,
            'win_rate': latest['win_rate'],
            'avg_leverage': sum(p['current_leverage'] for p in self.performance_history) / len(self.performance_history),
            'max_drawdown': max_drawdown
        }