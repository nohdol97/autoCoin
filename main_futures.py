#!/usr/bin/env python3
"""
AutoCoin Main Application with Futures Trading Support
"""
import asyncio
import logging
import signal
import sys
from typing import Optional

from src.futures_config import FuturesConfig
from src.logger import setup_logger
from src.exchange.binance_futures_client import BinanceFuturesClient
from src.telegram_bot.futures_bot import AutoCoinFuturesBot
from src.trading.futures_engine import FuturesTradingEngine
from src.trading.futures_position_manager import FuturesPositionManager
from src.monitoring.futures_monitor import FuturesMonitor
from src.monitoring.health_checker import HealthChecker
from src.monitoring.prometheus_metrics import PrometheusMetrics
from src.utils.error_handler import ErrorHandler
from src.utils.risk_manager import RiskManager
from src.exceptions import ComponentInitializationException, SystemException


class AutoCoinFuturesApp:
    """Main application class with futures trading support"""
    
    def __init__(self):
        self.config = FuturesConfig()
        self.logger = setup_logger('AutoCoinFutures')
        
        # Core components
        self.futures_client: Optional[BinanceFuturesClient] = None
        self.bot: Optional[AutoCoinFuturesBot] = None
        self.engine: Optional[FuturesTradingEngine] = None
        self.position_manager: Optional[FuturesPositionManager] = None
        self.risk_manager: Optional[RiskManager] = None
        
        # Monitoring components
        self.futures_monitor: Optional[FuturesMonitor] = None
        self.health_checker: Optional[HealthChecker] = None
        self.prometheus_metrics: Optional[PrometheusMetrics] = None
        self.error_handler: Optional[ErrorHandler] = None
        
        # Control
        self.shutdown_event = asyncio.Event()
        
    async def initialize(self):
        """Initialize all components"""
        try:
            self.logger.info("Initializing AutoCoin Futures System...")
            
            # Error handler
            self.error_handler = ErrorHandler(self.logger)
            
            # Initialize Futures Client
            try:
                self.futures_client = BinanceFuturesClient(
                    api_key=self.config.api_key,
                    api_secret=self.config.api_secret,
                    testnet=self.config.use_testnet
                )
                await self.futures_client.initialize()
                
                # Test connection
                if await self.futures_client.test_connection():
                    self.logger.info("Futures client initialized and connected")
                else:
                    raise Exception("Failed to connect to Binance Futures API")
                    
            except Exception as e:
                raise ComponentInitializationException("FuturesClient", str(e))
                
            # Initialize Risk Manager
            try:
                self.risk_manager = RiskManager(self.config.risk_percentage)
                self.logger.info("Risk manager initialized")
            except Exception as e:
                raise ComponentInitializationException("RiskManager", str(e))
                
            # Initialize Position Manager
            try:
                self.position_manager = FuturesPositionManager(
                    self.futures_client,
                    self.risk_manager
                )
                await self.position_manager.initialize()
                self.logger.info("Position manager initialized")
            except Exception as e:
                raise ComponentInitializationException("PositionManager", str(e))
                
            # Initialize Prometheus Metrics
            try:
                self.prometheus_metrics = PrometheusMetrics()
                self.prometheus_metrics.start_server(port=8000)
                self.logger.info("Prometheus metrics server started on port 8000")
            except Exception as e:
                self.logger.warning(f"Prometheus metrics initialization failed: {e}")
                self.prometheus_metrics = None
                
            # Initialize Futures Monitor
            try:
                self.futures_monitor = FuturesMonitor(
                    self.futures_client,
                    self.position_manager,
                    self.prometheus_metrics
                )
                self.logger.info("Futures monitor initialized")
            except Exception as e:
                raise ComponentInitializationException("FuturesMonitor", str(e))
                
            # Initialize Trading Engine
            try:
                self.engine = FuturesTradingEngine(self.config)
                await self.engine.initialize()
                
                # Set default strategy
                if self.config.default_futures_strategy:
                    self.engine.set_strategy(self.config.default_futures_strategy)
                    
                self.logger.info("Futures trading engine initialized")
            except Exception as e:
                raise ComponentInitializationException("TradingEngine", str(e))
                
            # Initialize Telegram Bot
            if self.config.telegram_token and self.config.chat_id:
                try:
                    self.bot = AutoCoinFuturesBot(self.config)
                    await self.bot.initialize()
                    
                    # Connect bot to engine
                    self.engine.set_telegram_bot(self.bot)
                    
                    self.logger.info("Telegram bot initialized")
                except Exception as e:
                    self.logger.warning(f"Telegram bot initialization failed: {e}")
                    self.bot = None
            else:
                self.logger.warning("Telegram credentials not provided, bot disabled")
                
            # Initialize Health Checker
            self.health_checker = HealthChecker()
            self.health_checker.register_component('futures_client', self.futures_client)
            self.health_checker.register_component('position_manager', self.position_manager)
            self.health_checker.register_component('trading_engine', self.engine)
            self.health_checker.register_component('futures_monitor', self.futures_monitor)
            
            if self.bot:
                self.health_checker.register_component('telegram_bot', self.bot)
                
            self.logger.info("Health checker initialized")
            
            self.logger.info("✅ AutoCoin Futures System initialized successfully")
            
        except ComponentInitializationException as e:
            self.logger.error(f"Failed to initialize {e.component}: {e.message}")
            await self.cleanup()
            raise
        except Exception as e:
            self.logger.error(f"Unexpected initialization error: {e}")
            await self.cleanup()
            raise SystemException(f"System initialization failed: {str(e)}")
            
    async def run(self):
        """Run the main application"""
        try:
            # Start monitoring
            await self.futures_monitor.start_monitoring()
            self.logger.info("Futures monitoring started")
            
            # Start health check loop
            health_task = asyncio.create_task(self.health_check_loop())
            
            # Start trading engine if strategy is set
            if self.engine.active_strategy and self.config.enable_futures:
                engine_task = asyncio.create_task(self.engine.start())
                self.logger.info(f"Trading engine started with strategy: {self.engine.active_strategy}")
            else:
                self.logger.info("Trading engine not started (no strategy set or futures disabled)")
                engine_task = None
                
            # Start telegram bot
            if self.bot:
                bot_task = asyncio.create_task(self.run_telegram_bot())
                self.logger.info("Telegram bot started")
            else:
                bot_task = None
                
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            # Cleanup tasks
            health_task.cancel()
            if engine_task:
                await self.engine.stop()
            if bot_task:
                bot_task.cancel()
                
        except Exception as e:
            self.logger.error(f"Runtime error: {e}")
            await self.error_handler.handle_error(e, critical=True)
            
    async def health_check_loop(self):
        """Periodic health check"""
        while not self.shutdown_event.is_set():
            try:
                health_status = await self.health_checker.check_all()
                
                if not health_status['healthy']:
                    unhealthy = [k for k, v in health_status['components'].items() if not v]
                    self.logger.warning(f"Unhealthy components: {unhealthy}")
                    
                    # Send alert if bot is available
                    if self.bot and 'telegram_bot' not in unhealthy:
                        alert_msg = f"⚠️ System Health Alert\nUnhealthy: {', '.join(unhealthy)}"
                        # await self.bot.send_notification(alert_msg)
                        
                # Update Prometheus metrics
                if self.prometheus_metrics:
                    self.prometheus_metrics.system_health.set(
                        1 if health_status['healthy'] else 0
                    )
                    
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
                
            await asyncio.sleep(60)  # Check every minute
            
    async def run_telegram_bot(self):
        """Run telegram bot"""
        if self.bot:
            try:
                # This would need to be implemented in the bot class
                # For now, just keep the task alive
                while not self.shutdown_event.is_set():
                    await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"Telegram bot error: {e}")
                
    async def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up resources...")
        
        # Stop monitoring
        if self.futures_monitor:
            await self.futures_monitor.stop_monitoring()
            
        # Stop trading engine
        if self.engine and self.engine.is_running:
            await self.engine.stop()
            
        # Close exchange connections
        if self.futures_client:
            await self.futures_client.close()
            
        # Stop Prometheus server
        if self.prometheus_metrics:
            self.prometheus_metrics.stop_server()
            
        self.logger.info("Cleanup completed")
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(sig, frame):
            self.logger.info(f"Received signal {sig}, shutting down...")
            self.shutdown_event.set()
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        

async def main():
    """Main entry point"""
    app = AutoCoinFuturesApp()
    
    try:
        # Initialize application
        await app.initialize()
        
        # Setup signal handlers
        app.setup_signal_handlers()
        
        # Run application
        await app.run()
        
    except Exception as e:
        logging.error(f"Application error: {e}")
        sys.exit(1)
        
    finally:
        await app.cleanup()
        

if __name__ == "__main__":
    # Create example config files if they don't exist
    config = FuturesConfig()
    if not os.path.exists('.env.futures.example'):
        config.create_example_env_file()
    if not os.path.exists('futures_config.json'):
        config.create_example_config_file()
        
    # Run the application
    asyncio.run(main())