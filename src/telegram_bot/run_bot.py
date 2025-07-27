#!/usr/bin/env python3
"""
Run the AutoCoin Telegram Bot
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import Config
from src.telegram_bot.bot import AutoCoinBot
from src.logger import get_logger

logger = get_logger('bot_runner')

def main():
    """Main entry point for the bot"""
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = Config()
        
        # Validate required settings
        if not config.telegram_token:
            logger.error("TELEGRAM_BOT_TOKEN is not set in .env file")
            sys.exit(1)
            
        if not config.chat_id:
            logger.error("TELEGRAM_CHAT_ID is not set in .env file")
            sys.exit(1)
            
        # Create and run bot
        logger.info("Starting AutoCoin Bot...")
        bot = AutoCoinBot(config)
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()