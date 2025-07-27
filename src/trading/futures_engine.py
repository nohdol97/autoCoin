"""
Extended Trading Engine with Futures Support
"""
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from enum import Enum

from ..config import Config
from ..exchange.binance_futures_client import BinanceFuturesClient
from ..strategies import StrategyManager
from ..strategies.base_strategy import BaseStrategy
from ..strategies.funding_rate_arbitrage import FundingRateArbitrageStrategy
from ..strategies.grid_trading import GridTradingStrategy
from ..strategies.long_short_switching import LongShortSwitchingStrategy
from ..strategies.volatility_breakout import VolatilityBreakoutStrategy
from ..telegram_bot.futures_bot import AutoCoinFuturesBot
from .futures_position_manager import FuturesPositionManager
from .market_data import MarketDataFetcher
from .order_executor import OrderExecutor
from .position_monitor import PositionMonitor
from ..utils.risk_manager import RiskManager
from ..logger import get_logger

logger = get_logger('futures_trading_engine')


class FuturesTradingEngine:
    """Extended trading engine with futures support"""
    
    def __init__(self, config: Config):
        self.config = config
        self.is_running = False
        
        # Initialize futures client
        self.futures_client = BinanceFuturesClient(
            config.api_key,
            config.api_secret,
            config.use_testnet
        )
        
        # Initialize risk manager
        self.risk_manager = RiskManager(config.risk_percentage)
        
        # Initialize position manager
        self.position_manager = FuturesPositionManager(
            self.futures_client,
            self.risk_manager
        )
        
        # Initialize strategies
        self.strategies: Dict[str, BaseStrategy] = {}
        self._initialize_strategies()
        
        # Active strategy
        self.active_strategy: Optional[str] = None
        
        # Trading parameters
        self.symbol = config.symbol
        self.max_capital_per_trade = config.base_amount * 3  # Allow 3x for futures
        self.trading_interval = 60  # seconds
        
        # Monitoring parameters
        self.monitor_interval = 10  # seconds
        self.risk_check_interval = 30  # seconds
        
        # Telegram bot reference
        self.telegram_bot: Optional[AutoCoinFuturesBot] = None
        
        # Tasks
        self._tasks: List[asyncio.Task] = []
        
        logger.info(f"Futures Trading Engine initialized for {self.symbol}")
        
    def _initialize_strategies(self):
        """Initialize futures trading strategies"""
        # Funding Rate Arbitrage
        self.strategies['funding_arbitrage'] = FundingRateArbitrageStrategy({
            'symbol': self.config.symbol,
            'min_funding_rate': 0.01,
            'funding_threshold': 0.005,
            'max_position_size': 0.3,
            'leverage': 2
        })
        
        # Grid Trading
        self.strategies['grid_trading'] = GridTradingStrategy({
            'symbol': self.config.symbol,
            'grid_levels': 10,
            'grid_spacing': 0.002,
            'grid_size_pct': 0.1,
            'leverage': 3
        })
        
        # Long-Short Switching
        self.strategies['long_short_switching'] = LongShortSwitchingStrategy({
            'symbol': self.config.symbol,
            'fast_ma_period': 20,
            'slow_ma_period': 50,
            'leverage': 5,
            'position_size_pct': 0.3
        })
        
        # Volatility Breakout
        self.strategies['volatility_breakout'] = VolatilityBreakoutStrategy({
            'symbol': self.config.symbol,
            'bb_period': 20,
            'leverage': 10,
            'position_size_pct': 0.2
        })
        
        logger.info(f"Initialized {len(self.strategies)} futures strategies")
        
    async def initialize(self):
        """Initialize async components"""
        await self.futures_client.initialize()
        await self.position_manager.initialize()
        logger.info("Futures engine async components initialized")
        
    def set_telegram_bot(self, bot: AutoCoinFuturesBot):
        """Set telegram bot for notifications"""
        self.telegram_bot = bot
        logger.info("Futures telegram bot connected")
        
    def set_strategy(self, strategy_name: str) -> bool:
        """Set active trading strategy"""
        if strategy_name not in self.strategies:
            logger.error(f"Strategy {strategy_name} not found")
            return False
            
        self.active_strategy = strategy_name
        logger.info(f"Active strategy set to: {strategy_name}")
        return True
        
    async def start(self):
        """Start the futures trading engine"""
        if self.is_running:
            logger.warning("Futures engine already running")
            return
            
        if not self.active_strategy:
            logger.error("No active strategy set")
            await self.send_notification("❌ 전략을 먼저 선택해주세요")
            return
            
        logger.info("Starting futures trading engine...")
        self.is_running = True
        
        try:
            # Create tasks
            self._tasks = [
                asyncio.create_task(self.trading_loop()),
                asyncio.create_task(self.position_monitoring_loop()),
                asyncio.create_task(self.risk_monitoring_loop()),
                asyncio.create_task(self.funding_monitoring_loop())
            ]
            
            # Send notification
            await self.send_notification(
                f"🚀 Futures Trading Started\n"
                f"Strategy: {self.active_strategy}\n"
                f"Symbol: {self.symbol}"
            )
            
            # Wait for tasks
            await asyncio.gather(*self._tasks)
            
        except Exception as e:
            logger.error(f"Futures engine error: {e}")
            await self.send_notification(f"❌ Futures Engine Error: {str(e)}")
            await self.stop()
            
    async def stop(self):
        """Stop the futures trading engine"""
        logger.info("Stopping futures trading engine...")
        self.is_running = False
        
        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
                
        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        
        # Cancel all open orders
        await self._cancel_all_orders()
        
        logger.info("Futures engine stopped")
        await self.send_notification("🛑 Futures Trading Stopped")
        
    async def trading_loop(self):
        """Main futures trading loop"""
        logger.info("Futures trading loop started")
        
        while self.is_running:
            try:
                # Check if we should trade
                if not await self._should_trade():
                    await asyncio.sleep(self.trading_interval)
                    continue
                    
                # Get active strategy
                strategy = self.strategies[self.active_strategy]
                
                # Analyze market
                signal = await strategy.analyze(self.futures_client, self.symbol)
                
                # Log signal
                logger.info(
                    f"Strategy signal: {signal['signal']} "
                    f"(confidence: {signal.get('confidence', 0):.2f})"
                )
                
                # Execute trade if signal is strong
                if signal['signal'] not in ['hold', None] and signal.get('confidence', 0) > 0.6:
                    # Get available capital
                    balance = await asyncio.to_thread(
                        self.futures_client.get_futures_balance
                    )
                    available_capital = balance['USDT']['free']
                    
                    # Calculate trade capital
                    trade_capital = min(
                        available_capital * 0.9,  # Use 90% of available
                        self.max_capital_per_trade
                    )
                    
                    # Execute trade
                    result = await strategy.execute_trade(
                        self.futures_client,
                        signal,
                        trade_capital
                    )
                    
                    if result:
                        await self.send_notification(
                            f"✅ Trade Executed\n"
                            f"Strategy: {self.active_strategy}\n"
                            f"Type: {result.get('type', 'Unknown')}\n"
                            f"Details: {self._format_trade_result(result)}"
                        )
                        
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await self.send_notification(f"⚠️ Trading Error: {str(e)}")
                
            await asyncio.sleep(self.trading_interval)
            
    async def position_monitoring_loop(self):
        """Monitor and update positions"""
        logger.info("Position monitoring loop started")
        
        while self.is_running:
            try:
                # Update positions
                await self.position_manager.update_positions()
                
                # Check for trailing stops (for certain strategies)
                if self.active_strategy == 'long_short_switching':
                    strategy = self.strategies[self.active_strategy]
                    for symbol, position in self.position_manager.positions.items():
                        ticker = await asyncio.to_thread(
                            self.futures_client.get_futures_ticker,
                            symbol
                        )
                        await strategy.update_trailing_stop(
                            self.futures_client,
                            ticker['last']
                        )
                        
            except Exception as e:
                logger.error(f"Position monitoring error: {e}")
                
            await asyncio.sleep(self.monitor_interval)
            
    async def risk_monitoring_loop(self):
        """Monitor risk metrics and liquidation"""
        logger.info("Risk monitoring loop started")
        
        while self.is_running:
            try:
                # Get risk metrics
                risk_metrics = await self.position_manager.get_risk_metrics()
                
                # Check if overleveraged
                if risk_metrics.is_overleveraged:
                    await self.send_notification(
                        "⚠️ Risk Alert: Account is overleveraged!\n"
                        f"Margin Level: {risk_metrics.margin_level:.1f}%"
                    )
                    
                # Check liquidation risk
                at_risk = await self.position_manager.check_liquidation_risk()
                for position in at_risk:
                    if position['risk_level'] == 'HIGH':
                        await self.send_notification(
                            f"🚨 Liquidation Risk HIGH\n"
                            f"Symbol: {position['symbol']}\n"
                            f"Distance: {position['distance_percentage']:.2f}%"
                        )
                        
            except Exception as e:
                logger.error(f"Risk monitoring error: {e}")
                
            await asyncio.sleep(self.risk_check_interval)
            
    async def funding_monitoring_loop(self):
        """Monitor funding rates for arbitrage strategy"""
        if self.active_strategy != 'funding_arbitrage':
            return
            
        logger.info("Funding monitoring loop started")
        
        while self.is_running:
            try:
                # Get funding rate
                funding = await self.position_manager.get_funding_rate(self.symbol)
                
                if funding and abs(funding.rate) > 0.01:  # 1% threshold
                    await self.send_notification(
                        f"💰 High Funding Rate Alert\n"
                        f"Rate: {funding.rate:.4%}\n"
                        f"Annual: {funding.annual_rate:.2f}%\n"
                        f"Next in: {funding.hours_until_funding:.1f}h"
                    )
                    
            except Exception as e:
                logger.error(f"Funding monitoring error: {e}")
                
            # Check every hour
            await asyncio.sleep(3600)
            
    async def _should_trade(self) -> bool:
        """Check if we should execute trades"""
        # Check risk metrics
        risk_metrics = await self.position_manager.get_risk_metrics()
        
        # Don't trade if overleveraged
        if risk_metrics.is_overleveraged:
            logger.warning("Skipping trade - overleveraged")
            return False
            
        # Don't trade if too many positions
        if risk_metrics.positions_count >= 5:
            logger.warning("Skipping trade - too many positions")
            return False
            
        # Check margin usage
        if risk_metrics.margin_usage_percentage > 80:
            logger.warning("Skipping trade - high margin usage")
            return False
            
        return True
        
    async def _cancel_all_orders(self):
        """Cancel all open futures orders"""
        try:
            open_orders = await asyncio.to_thread(
                self.futures_client.futures_exchange.fetch_open_orders,
                self.symbol
            )
            
            for order in open_orders:
                await asyncio.to_thread(
                    self.futures_client.futures_exchange.cancel_order,
                    order['id'],
                    self.symbol
                )
                
            logger.info(f"Cancelled {len(open_orders)} open orders")
            
        except Exception as e:
            logger.error(f"Failed to cancel orders: {e}")
            
    def _format_trade_result(self, result: Dict) -> str:
        """Format trade result for notification"""
        parts = []
        
        if 'position_size' in result:
            parts.append(f"Size: {result['position_size']}")
            
        if 'leverage' in result:
            parts.append(f"Leverage: {result['leverage']}x")
            
        if 'stop_loss' in result and result['stop_loss']:
            parts.append(f"SL: ${result['stop_loss']:,.2f}")
            
        if 'take_profit' in result and result['take_profit']:
            parts.append(f"TP: ${result['take_profit']:,.2f}")
            
        return ", ".join(parts)
        
    async def send_notification(self, message: str):
        """Send notification via telegram"""
        if self.telegram_bot:
            try:
                # This would need to be implemented in the telegram bot
                logger.info(f"Notification: {message}")
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
                
    def get_status(self) -> Dict:
        """Get engine status"""
        return {
            'running': self.is_running,
            'active_strategy': self.active_strategy,
            'symbol': self.symbol,
            'positions': len(self.position_manager.positions),
            'available_strategies': list(self.strategies.keys())
        }