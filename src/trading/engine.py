"""
Main trading engine that orchestrates all trading components
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from ..config import Config
from ..exchange.binance_client import BinanceClient
from ..strategies import StrategyManager, Signal, Position
from ..telegram_bot.bot import AutoCoinBot
from .market_data import MarketDataFetcher
from .order_executor import OrderExecutor
from .position_monitor import PositionMonitor
from ..logger import get_logger

logger = get_logger('trading_engine')


class EngineState(Enum):
    """Trading engine states"""
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    ERROR = "ERROR"


class TradingEngine:
    """Main trading engine that coordinates all components"""
    
    def __init__(self, config: Config):
        self.config = config
        self.state = EngineState.STOPPED
        
        # Initialize components
        self.binance_client = BinanceClient(
            config.api_key,
            config.api_secret,
            config.use_testnet
        )
        
        self.strategy_manager = StrategyManager(config.__dict__)
        self.market_data = MarketDataFetcher(self.binance_client, config.symbol)
        self.order_executor = OrderExecutor(self.binance_client)
        self.position_monitor = PositionMonitor(self.binance_client)
        
        # Trading parameters
        self.symbol = config.symbol
        self.base_amount = config.base_amount
        self.max_positions = config.max_positions
        
        # Loop control
        self.trading_interval = 60  # seconds between strategy checks
        self.is_running = False
        
        # Telegram bot reference (optional)
        self.telegram_bot: Optional[AutoCoinBot] = None
        
        logger.info(f"Trading Engine initialized for {self.symbol}")
        
    def set_telegram_bot(self, bot: AutoCoinBot):
        """Set telegram bot for notifications"""
        self.telegram_bot = bot
        logger.info("Telegram bot connected to trading engine")
        
    async def start(self):
        """Start the trading engine"""
        if self.state == EngineState.RUNNING:
            logger.warning("Trading engine already running")
            return
            
        logger.info("Starting trading engine...")
        self.state = EngineState.STARTING
        self.is_running = True
        
        try:
            # Start component tasks
            tasks = [
                asyncio.create_task(self.market_data.start_price_stream()),
                asyncio.create_task(self.position_monitor.start_monitoring()),
                asyncio.create_task(self.trading_loop())
            ]
            
            self.state = EngineState.RUNNING
            logger.info("Trading engine started successfully")
            
            # Send notification
            await self.send_notification(
                "🚀 Trading Engine Started\n"
                f"Symbol: {self.symbol}\n"
                f"Strategy: {self.strategy_manager.active_strategy or 'None'}"
            )
            
            # Wait for tasks
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Trading engine error: {e}")
            self.state = EngineState.ERROR
            await self.send_notification(f"❌ Trading Engine Error: {str(e)}")
            
    async def stop(self):
        """Stop the trading engine"""
        logger.info("Stopping trading engine...")
        self.state = EngineState.STOPPING
        self.is_running = False
        
        # Stop components
        self.market_data.stop_price_stream()
        self.position_monitor.stop_monitoring()
        
        # Cancel all open orders
        cancelled = self.order_executor.cancel_all_orders()
        logger.info(f"Cancelled {cancelled} open orders")
        
        self.state = EngineState.STOPPED
        logger.info("Trading engine stopped")
        
        # Send notification
        await self.send_notification("🛑 Trading Engine Stopped")
        
    async def pause(self):
        """Pause trading (keep monitoring positions)"""
        if self.state != EngineState.RUNNING:
            logger.warning("Cannot pause - engine not running")
            return
            
        self.state = EngineState.PAUSED
        logger.info("Trading engine paused")
        await self.send_notification("⏸ Trading Engine Paused")
        
    async def resume(self):
        """Resume trading"""
        if self.state != EngineState.PAUSED:
            logger.warning("Cannot resume - engine not paused")
            return
            
        self.state = EngineState.RUNNING
        logger.info("Trading engine resumed")
        await self.send_notification("▶️ Trading Engine Resumed")
        
    async def trading_loop(self):
        """Main trading loop"""
        logger.info("Trading loop started")
        
        while self.is_running:
            try:
                if self.state == EngineState.RUNNING:
                    await self.execute_trading_cycle()
                    
                await asyncio.sleep(self.trading_interval)
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await self.send_notification(f"⚠️ Trading loop error: {str(e)}")
                await asyncio.sleep(self.trading_interval)
                
    async def execute_trading_cycle(self):
        """Execute one trading cycle"""
        try:
            # Check if we have an active strategy
            strategy = self.strategy_manager.get_active_strategy()
            if not strategy:
                logger.debug("No active strategy selected")
                return
                
            # Check position limits
            if len(self.position_monitor.positions) >= self.max_positions:
                logger.debug(f"Max positions reached ({self.max_positions})")
                return
                
            # Get market data
            required_candles = strategy.get_required_candles()
            ohlcv = self.market_data.fetch_ohlcv('1h', required_candles + 10)
            
            if ohlcv.empty:
                logger.warning("No market data available")
                return
                
            current_price = self.market_data.get_current_price()
            if not current_price:
                logger.warning("No current price available")
                return
                
            # Check existing position for this symbol
            if self.position_monitor.has_position(self.symbol):
                # Check exit conditions
                position = self.position_monitor.get_position(self.symbol)
                exit_reason = self.position_monitor.check_exit_conditions(
                    self.symbol, current_price
                )
                
                if exit_reason:
                    await self.close_position(position, exit_reason)
                else:
                    # Let strategy decide if it wants to exit
                    signal = strategy.analyze(ohlcv, current_price)
                    if signal == Signal.SELL and position.side == "LONG":
                        await self.close_position(position, "STRATEGY_SIGNAL")
                        
            else:
                # Look for entry signal
                signal = strategy.analyze(ohlcv, current_price)
                
                if signal == Signal.BUY:
                    await self.open_position(strategy, current_price)
                    
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            
    async def open_position(self, strategy, entry_price: float):
        """Open a new position"""
        try:
            # Calculate position size
            balance = self.binance_client.get_balance()
            available_usdt = balance.get('free', {}).get('USDT', 0)
            
            if available_usdt < self.base_amount:
                logger.warning(f"Insufficient balance: {available_usdt} USDT")
                return
                
            position_size = strategy.calculate_position_size(
                self.base_amount, entry_price
            )
            
            # Create position object
            position = strategy.open_position(
                symbol=self.symbol,
                side="LONG",  # Currently only supporting long positions
                entry_price=entry_price,
                quantity=position_size
            )
            
            # Execute entry order
            order = self.order_executor.execute_position_entry(position)
            
            if order and order.status.value == "FILLED":
                # Add to position monitor
                self.position_monitor.add_position(position)
                
                # Send notification
                await self.send_notification(
                    f"📈 Position Opened\n"
                    f"Strategy: {strategy.name}\n"
                    f"Size: {position_size:.8f} BTC\n"
                    f"Entry: ${entry_price:,.2f}\n"
                    f"SL: ${position.stop_loss:,.2f}\n"
                    f"TP: ${position.take_profit:,.2f}"
                )
                
                logger.info(f"Position opened: {position.to_dict()}")
            else:
                logger.error("Failed to execute entry order")
                strategy.position = None  # Reset strategy position
                
        except Exception as e:
            logger.error(f"Error opening position: {e}")
            
    async def close_position(self, position: Position, reason: str):
        """Close an existing position"""
        try:
            current_price = self.market_data.get_current_price()
            
            # Execute exit order
            order = self.order_executor.execute_position_exit(position)
            
            if order and order.status.value == "FILLED":
                # Close position in monitor
                closed = self.position_monitor.close_position(
                    position.symbol, order.average_price
                )
                
                if closed:
                    # Update strategy
                    strategy = self.strategy_manager.get_active_strategy()
                    if strategy:
                        strategy.history.append(closed)
                        strategy.position = None
                        
                    # Send notification
                    emoji = "🟢" if closed.pnl > 0 else "🔴"
                    await self.send_notification(
                        f"{emoji} Position Closed ({reason})\n"
                        f"PnL: ${closed.pnl:.2f} ({closed.pnl_percentage:.2f}%)\n"
                        f"Entry: ${closed.entry_price:,.2f}\n"
                        f"Exit: ${closed.exit_price:,.2f}"
                    )
                    
                    logger.info(f"Position closed: {closed.to_dict()}")
            else:
                logger.error("Failed to execute exit order")
                
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            
    async def send_notification(self, message: str):
        """Send notification via Telegram"""
        try:
            if self.telegram_bot and self.telegram_bot.app:
                await self.telegram_bot.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            
    def get_engine_status(self) -> Dict[str, Any]:
        """Get current engine status"""
        stats = self.position_monitor.get_statistics()
        
        return {
            'state': self.state.value,
            'symbol': self.symbol,
            'active_strategy': self.strategy_manager.active_strategy,
            'current_price': self.market_data.get_current_price(),
            'positions': stats['active_positions'],
            'total_pnl': stats['total_pnl'],
            'win_rate': stats['win_rate'],
            'last_update': self.market_data.last_update.isoformat() if self.market_data.last_update else None
        }
        
    def emergency_stop(self):
        """Emergency stop - close all positions and stop engine"""
        logger.warning("EMERGENCY STOP INITIATED")
        
        # Close all positions
        closed = self.position_monitor.emergency_close_all()
        
        # Cancel all orders
        self.order_executor.cancel_all_orders()
        
        # Stop engine
        asyncio.create_task(self.stop())
        
        logger.warning(f"Emergency stop completed. Closed {len(closed)} positions")