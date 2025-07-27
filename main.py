#!/usr/bin/env python3
import asyncio
import logging
import signal
import sys
from typing import Optional

from src.config import Config
from src.logger import setup_logger
from src.exchange.binance_client import BinanceClient
from src.telegram_bot.bot import TelegramBot
from src.trading.engine import TradingEngine
from src.strategies.strategy_manager import StrategyManager
from src.recommendation.strategy_recommender import StrategyRecommender
from src.monitoring.health_checker import HealthChecker
from src.monitoring.metrics_collector import MetricsCollector
from src.utils.error_handler import ErrorHandler
from src.exceptions import ComponentInitializationException, SystemException


class AutoCoinApp:
    def __init__(self):
        self.config = Config()
        self.logger = setup_logger('AutoCoin')
        self.exchange: Optional[BinanceClient] = None
        self.bot: Optional[TelegramBot] = None
        self.strategy_manager: Optional[StrategyManager] = None
        self.recommender: Optional[StrategyRecommender] = None
        self.engine: Optional[TradingEngine] = None
        self.health_checker: Optional[HealthChecker] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        self.error_handler: Optional[ErrorHandler] = None
        self.shutdown_event = asyncio.Event()
        
    async def initialize(self):
        """모든 컴포넌트 초기화"""
        try:
            self.logger.info("AutoCoin 시스템 초기화 중...")
            
            # 에러 핸들러 초기화
            self.error_handler = ErrorHandler(self.logger)
            
            # Exchange 클라이언트 초기화
            try:
                self.exchange = BinanceClient(
                    api_key=self.config.binance_api_key,
                    api_secret=self.config.binance_api_secret,
                    testnet=self.config.binance_testnet
                )
                await self.exchange.initialize()
                self.logger.info("Exchange 클라이언트 초기화 완료")
            except Exception as e:
                raise ComponentInitializationException("Exchange", str(e))
            
            # 전략 매니저 초기화
            try:
                self.strategy_manager = StrategyManager()
                self.logger.info("전략 매니저 초기화 완료")
            except Exception as e:
                raise ComponentInitializationException("StrategyManager", str(e))
            
            # 전략 추천 시스템 초기화
            try:
                self.recommender = StrategyRecommender(self.exchange)
                self.logger.info("전략 추천 시스템 초기화 완료")
            except Exception as e:
                raise ComponentInitializationException("StrategyRecommender", str(e))
            
            # Trading Engine 초기화
            try:
                self.engine = TradingEngine(
                    exchange=self.exchange,
                    strategy_manager=self.strategy_manager,
                    config=self.config
                )
                self.logger.info("Trading Engine 초기화 완료")
            except Exception as e:
                raise ComponentInitializationException("TradingEngine", str(e))
            
            # Telegram Bot 초기화
            try:
                self.bot = TelegramBot(
                    token=self.config.telegram_bot_token,
                    chat_id=self.config.telegram_chat_id,
                    engine=self.engine,
                    exchange=self.exchange,
                    strategy_manager=self.strategy_manager,
                    recommender=self.recommender
                )
                await self.bot.initialize()
                self.logger.info("Telegram Bot 초기화 완료")
            except Exception as e:
                raise ComponentInitializationException("TelegramBot", str(e))
            
            # Trading Engine에 Bot 연결
            self.engine.set_notifier(self.bot)
            
            # 모니터링 컴포넌트 초기화
            self.health_checker = HealthChecker()
            self.health_checker.register_component('exchange', self.exchange)
            self.health_checker.register_component('telegram_bot', self.bot)
            self.health_checker.register_component('trading_engine', self.engine)
            
            self.metrics_collector = MetricsCollector()
            self.metrics_collector.register_component('trading_engine', self.engine)
            
            self.logger.info("✅ AutoCoin 시스템 초기화 완료")
            
        except ComponentInitializationException as e:
            self.logger.error(f"컴포넌트 초기화 실패: {e}")
            await self.error_handler.handle_error(e)
            raise
        except Exception as e:
            self.logger.error(f"초기화 중 예상치 못한 오류: {e}")
            raise SystemException(f"System initialization failed: {str(e)}")
            
    async def start(self):
        """애플리케이션 시작"""
        try:
            await self.initialize()
            
            # 시그널 핸들러 설정
            self.setup_signal_handlers()
            
            # 컴포넌트들을 비동기로 실행
            tasks = [
                asyncio.create_task(self.bot.start()),
                asyncio.create_task(self.engine.monitor_loop()),
                asyncio.create_task(self.health_check_loop()),
                asyncio.create_task(self.shutdown_event.wait())
            ]
            
            self.logger.info("🚀 AutoCoin 시스템 시작됨")
            
            # 모든 태스크가 완료될 때까지 대기
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except KeyboardInterrupt:
            self.logger.info("키보드 인터럽트 감지")
        except Exception as e:
            self.logger.error(f"실행 중 오류 발생: {e}")
        finally:
            await self.shutdown()
            
    async def shutdown(self):
        """애플리케이션 종료"""
        self.logger.info("AutoCoin 시스템 종료 중...")
        
        # Trading Engine 종료
        if self.engine and self.engine.is_running:
            await self.engine.stop()
            
        # Telegram Bot 종료
        if self.bot:
            await self.bot.stop()
            
        # Exchange 연결 종료
        if self.exchange:
            await self.exchange.close()
            
        self.logger.info("✅ AutoCoin 시스템 종료 완료")
        
    async def health_check_loop(self):
        """주기적인 상태 체크"""
        while not self.shutdown_event.is_set():
            try:
                # 헬스 체크 실행
                if self.health_checker:
                    health_results = await self.health_checker.check_all()
                    
                    # 불건전한 컴포넌트 확인
                    unhealthy = [name for name, status in health_results.items() if not status.is_healthy]
                    if unhealthy:
                        self.logger.warning(f"불건전한 컴포넌트: {', '.join(unhealthy)}")
                        
                        # Telegram으로 알림
                        if self.bot and 'telegram' not in unhealthy:
                            summary = self.health_checker.get_summary(health_results)
                            await self.bot.send_notification(f"⚠️ 시스템 경고\n\n{summary}")
                            
                # 메트릭 수집
                if self.metrics_collector:
                    await self.metrics_collector.collect_metrics()
                    
            except Exception as e:
                self.logger.error(f"Health check 오류: {e}")
                await self.error_handler.handle_error(e, {"context": "health_check_loop"})
                
            await asyncio.sleep(300)  # 5분마다 체크
            
    def setup_signal_handlers(self):
        """시그널 핸들러 설정"""
        def signal_handler(signum, frame):
            self.logger.info(f"시그널 {signum} 수신")
            asyncio.create_task(self.shutdown_event.set())
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """메인 함수"""
    app = AutoCoinApp()
    await app.start()


if __name__ == "__main__":
    # Python 버전 체크
    if sys.version_info < (3, 8):
        print("Python 3.8 이상이 필요합니다.")
        sys.exit(1)
        
    # 이벤트 루프 실행
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램이 종료되었습니다.")