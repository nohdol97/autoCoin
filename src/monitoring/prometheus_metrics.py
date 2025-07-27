from prometheus_client import Counter, Gauge, Histogram, Info
from prometheus_client import start_http_server
import time
import logging
from typing import Optional


class PrometheusMetrics:
    """Prometheus 메트릭 수집기"""
    
    def __init__(self, port: int = 8080):
        self.logger = logging.getLogger(__name__)
        self.port = port
        
        # System Info
        self.system_info = Info('autocoin_system', 'AutoCoin system information')
        
        # Trading Metrics
        self.trades_total = Counter('autocoin_trades_total', 'Total number of trades', ['strategy', 'side'])
        self.trades_successful = Counter('autocoin_trades_successful', 'Number of successful trades', ['strategy'])
        self.trades_failed = Counter('autocoin_trades_failed', 'Number of failed trades', ['strategy'])
        
        # Position Metrics
        self.position_count = Gauge('autocoin_position_count', 'Current number of open positions')
        self.position_value = Gauge('autocoin_position_value', 'Total value of open positions in USDT')
        self.position_pnl = Gauge('autocoin_position_pnl', 'Current unrealized PnL in USDT')
        
        # Balance Metrics
        self.balance_total = Gauge('autocoin_balance_total', 'Total account balance in USDT')
        self.balance_free = Gauge('autocoin_balance_free', 'Free balance in USDT')
        self.balance_locked = Gauge('autocoin_balance_locked', 'Locked balance in USDT')
        
        # Performance Metrics
        self.win_rate = Gauge('autocoin_win_rate', 'Current win rate percentage')
        self.sharpe_ratio = Gauge('autocoin_sharpe_ratio', 'Current Sharpe ratio')
        self.max_drawdown = Gauge('autocoin_max_drawdown', 'Maximum drawdown percentage')
        
        # API Metrics
        self.api_requests = Counter('autocoin_api_requests_total', 'Total API requests', ['endpoint', 'status'])
        self.api_latency = Histogram('autocoin_api_latency_seconds', 'API request latency', ['endpoint'])
        self.api_rate_limit_remaining = Gauge('autocoin_api_rate_limit_remaining', 'Remaining API rate limit')
        self.api_rate_limit_total = Gauge('autocoin_api_rate_limit_total', 'Total API rate limit')
        
        # System Metrics
        self.trading_engine_running = Gauge('autocoin_trading_engine_running', 'Trading engine status (1=running, 0=stopped)')
        self.errors_total = Counter('autocoin_errors_total', 'Total number of errors', ['type'])
        self.last_trade_timestamp = Gauge('autocoin_last_trade_timestamp', 'Timestamp of last trade')
        
        # Strategy Metrics
        self.strategy_signals = Counter('autocoin_strategy_signals_total', 'Total strategy signals', ['strategy', 'signal'])
        self.strategy_active = Gauge('autocoin_strategy_active', 'Active strategy', ['strategy'])
        
    def start_server(self):
        """Prometheus HTTP 서버 시작"""
        try:
            start_http_server(self.port)
            self.logger.info(f"Prometheus metrics server started on port {self.port}")
            
            # 시스템 정보 설정
            self.system_info.info({
                'version': '1.0.0',
                'environment': 'production'
            })
            
        except Exception as e:
            self.logger.error(f"Failed to start Prometheus server: {e}")
            
    def record_trade(self, strategy: str, side: str, success: bool):
        """거래 기록"""
        self.trades_total.labels(strategy=strategy, side=side).inc()
        
        if success:
            self.trades_successful.labels(strategy=strategy).inc()
        else:
            self.trades_failed.labels(strategy=strategy).inc()
            
        self.last_trade_timestamp.set(time.time())
        
    def update_position_metrics(self, count: int, value: float, pnl: float):
        """포지션 메트릭 업데이트"""
        self.position_count.set(count)
        self.position_value.set(value)
        self.position_pnl.set(pnl)
        
    def update_balance_metrics(self, total: float, free: float, locked: float):
        """잔고 메트릭 업데이트"""
        self.balance_total.set(total)
        self.balance_free.set(free)
        self.balance_locked.set(locked)
        
    def update_performance_metrics(self, win_rate: float, sharpe: float, drawdown: float):
        """성과 메트릭 업데이트"""
        self.win_rate.set(win_rate)
        self.sharpe_ratio.set(sharpe)
        self.max_drawdown.set(drawdown)
        
    def record_api_request(self, endpoint: str, status: str, latency: float):
        """API 요청 기록"""
        self.api_requests.labels(endpoint=endpoint, status=status).inc()
        self.api_latency.labels(endpoint=endpoint).observe(latency)
        
    def update_api_rate_limit(self, remaining: int, total: int):
        """API Rate Limit 업데이트"""
        self.api_rate_limit_remaining.set(remaining)
        self.api_rate_limit_total.set(total)
        
    def set_trading_engine_status(self, running: bool):
        """Trading Engine 상태 설정"""
        self.trading_engine_running.set(1 if running else 0)
        
    def record_error(self, error_type: str):
        """에러 기록"""
        self.errors_total.labels(type=error_type).inc()
        
    def record_strategy_signal(self, strategy: str, signal: str):
        """전략 신호 기록"""
        self.strategy_signals.labels(strategy=strategy, signal=signal).inc()
        
    def set_active_strategy(self, strategy: str):
        """활성 전략 설정"""
        # 모든 전략을 비활성화
        for s in ['breakout', 'scalping', 'trend']:
            self.strategy_active.labels(strategy=s).set(0)
            
        # 현재 전략만 활성화
        self.strategy_active.labels(strategy=strategy).set(1)