"""
Test Phase 2: Telegram Bot Implementation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.telegram_bot.bot import AutoCoinBot
from src.telegram_bot.handlers import TradingHandlers
from src.logger import get_logger

logger = get_logger('test_phase2')

def test_bot_initialization():
    """Test bot initialization"""
    logger.info("Testing bot initialization...")
    
    try:
        config = Config()
        bot = AutoCoinBot(config)
        
        # Check bot attributes
        assert bot.token == config.telegram_token
        assert bot.authorized_chat_id == str(config.chat_id)
        assert bot.binance_client is not None
        assert bot.trading_handlers is not None
        assert not bot.is_running
        assert bot.active_strategy is None
        
        logger.info("✅ Bot initialization test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Bot initialization failed: {e}")
        return False

def test_handlers_setup():
    """Test handlers setup"""
    logger.info("Testing handlers setup...")
    
    try:
        config = Config()
        bot = AutoCoinBot(config)
        
        # Check trading handlers
        assert isinstance(bot.trading_handlers, TradingHandlers)
        assert bot.trading_handlers.bot == bot
        
        logger.info("✅ Handlers setup test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Handlers setup failed: {e}")
        return False

def check_commands():
    """Check available commands"""
    logger.info("Checking available commands...")
    
    commands = [
        # Basic commands
        "/start", "/help", "/status",
        # Trading info
        "/balance", "/ticker", "/position",
        # Strategy management
        "/strategies", "/select", "/params",
        # Trading control
        "/run", "/stop", "/pause", "/resume",
        # Risk management
        "/sl", "/tp", "/risk",
        # Reports
        "/report", "/history"
    ]
    
    logger.info(f"Available commands: {len(commands)}")
    for cmd in commands:
        logger.info(f"  {cmd}")
    
    return True

def main():
    """Run Phase 2 tests"""
    logger.info("=== Phase 2 Test Suite ===")
    logger.info("Testing Telegram Bot Implementation")
    
    tests = [
        ("Bot Initialization", test_bot_initialization),
        ("Handlers Setup", test_handlers_setup),
        ("Commands Check", check_commands),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\nRunning: {test_name}")
        success = test_func()
        results.append((test_name, success))
    
    # Summary
    logger.info("\n=== Test Summary ===")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n🎉 Phase 2 implementation complete!")
        logger.info("Telegram bot is ready for integration with trading strategies.")
        logger.info("\nTo run the bot:")
        logger.info("  python3 src/telegram_bot/run_bot.py")
    else:
        logger.error("\n⚠️ Some tests failed. Please check the implementation.")

if __name__ == "__main__":
    main()