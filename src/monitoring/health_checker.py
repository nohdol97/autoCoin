import asyncio
import psutil
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class HealthStatus:
    """헬스 체크 결과"""
    component: str
    is_healthy: bool
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


class HealthChecker:
    """시스템 상태 체크"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.checks = {
            'system': self.check_system_resources,
            'exchange': self.check_exchange_connection,
            'telegram': self.check_telegram_bot,
            'trading': self.check_trading_engine
        }
        self.components = {}
        
    def register_component(self, name: str, component: Any):
        """모니터링할 컴포넌트 등록"""
        self.components[name] = component
        
    async def check_all(self) -> Dict[str, HealthStatus]:
        """모든 컴포넌트 상태 체크"""
        results = {}
        
        for name, check_func in self.checks.items():
            try:
                results[name] = await check_func()
            except Exception as e:
                self.logger.error(f"{name} 체크 중 오류: {e}")
                results[name] = HealthStatus(
                    component=name,
                    is_healthy=False,
                    message=f"체크 실패: {str(e)}",
                    timestamp=datetime.now()
                )
                
        return results
        
    async def check_system_resources(self) -> HealthStatus:
        """시스템 리소스 체크"""
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_mb = memory.available / 1024 / 1024
            
            # 디스크 사용률
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = disk.free / 1024 / 1024 / 1024
            
            # 프로세스 정보
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / 1024 / 1024
            
            # 상태 판단
            is_healthy = (
                cpu_percent < 80 and
                memory_percent < 85 and
                disk_percent < 90 and
                process_memory_mb < 800
            )
            
            message = "시스템 리소스 정상" if is_healthy else "시스템 리소스 경고"
            
            return HealthStatus(
                component='system',
                is_healthy=is_healthy,
                message=message,
                timestamp=datetime.now(),
                details={
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'memory_available_mb': memory_available_mb,
                    'disk_percent': disk_percent,
                    'disk_free_gb': disk_free_gb,
                    'process_memory_mb': process_memory_mb
                }
            )
            
        except Exception as e:
            return HealthStatus(
                component='system',
                is_healthy=False,
                message=f"시스템 체크 실패: {str(e)}",
                timestamp=datetime.now()
            )
            
    async def check_exchange_connection(self) -> HealthStatus:
        """거래소 연결 상태 체크"""
        exchange = self.components.get('exchange')
        if not exchange:
            return HealthStatus(
                component='exchange',
                is_healthy=False,
                message="Exchange 컴포넌트가 등록되지 않음",
                timestamp=datetime.now()
            )
            
        try:
            # API 연결 테스트
            await exchange.test_connection()
            
            # 잔고 조회 테스트
            balance = await exchange.get_balance()
            
            return HealthStatus(
                component='exchange',
                is_healthy=True,
                message="거래소 연결 정상",
                timestamp=datetime.now(),
                details={
                    'connected': True,
                    'has_balance': balance is not None
                }
            )
            
        except Exception as e:
            return HealthStatus(
                component='exchange',
                is_healthy=False,
                message=f"거래소 연결 실패: {str(e)}",
                timestamp=datetime.now()
            )
            
    async def check_telegram_bot(self) -> HealthStatus:
        """텔레그램 봇 상태 체크"""
        bot = self.components.get('telegram_bot')
        if not bot:
            return HealthStatus(
                component='telegram',
                is_healthy=False,
                message="Telegram Bot 컴포넌트가 등록되지 않음",
                timestamp=datetime.now()
            )
            
        try:
            # 봇 상태 확인
            is_running = bot.is_running if hasattr(bot, 'is_running') else False
            
            return HealthStatus(
                component='telegram',
                is_healthy=is_running,
                message="텔레그램 봇 실행 중" if is_running else "텔레그램 봇 정지됨",
                timestamp=datetime.now(),
                details={
                    'is_running': is_running
                }
            )
            
        except Exception as e:
            return HealthStatus(
                component='telegram',
                is_healthy=False,
                message=f"텔레그램 봇 체크 실패: {str(e)}",
                timestamp=datetime.now()
            )
            
    async def check_trading_engine(self) -> HealthStatus:
        """트레이딩 엔진 상태 체크"""
        engine = self.components.get('trading_engine')
        if not engine:
            return HealthStatus(
                component='trading',
                is_healthy=False,
                message="Trading Engine 컴포넌트가 등록되지 않음",
                timestamp=datetime.now()
            )
            
        try:
            # 엔진 상태 확인
            is_running = engine.is_running if hasattr(engine, 'is_running') else False
            active_strategy = engine.active_strategy.name if hasattr(engine, 'active_strategy') and engine.active_strategy else None
            
            return HealthStatus(
                component='trading',
                is_healthy=True,
                message=f"트레이딩 엔진 {'실행 중' if is_running else '정지됨'}",
                timestamp=datetime.now(),
                details={
                    'is_running': is_running,
                    'active_strategy': active_strategy
                }
            )
            
        except Exception as e:
            return HealthStatus(
                component='trading',
                is_healthy=False,
                message=f"트레이딩 엔진 체크 실패: {str(e)}",
                timestamp=datetime.now()
            )
            
    def get_summary(self, results: Dict[str, HealthStatus]) -> str:
        """헬스 체크 결과 요약"""
        healthy_count = sum(1 for status in results.values() if status.is_healthy)
        total_count = len(results)
        
        summary = f"시스템 상태: {healthy_count}/{total_count} 정상\n\n"
        
        for name, status in results.items():
            emoji = "✅" if status.is_healthy else "❌"
            summary += f"{emoji} {name}: {status.message}\n"
            
            if status.details and not status.is_healthy:
                for key, value in status.details.items():
                    summary += f"  - {key}: {value}\n"
                    
        return summary