from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import logging
from typing import Optional, Dict, Any
import asyncio
from datetime import datetime

from ..config import Config
from ..exchange.binance_client import BinanceClient
from ..logger import get_logger
from .handlers import TradingHandlers

logger = get_logger('telegram_bot')

class AutoCoinBot:
    """Main Telegram Bot class for AutoCoin trading bot"""
    
    def __init__(self, config: Config):
        self.config = config
        self.token = config.telegram_token
        self.authorized_chat_id = str(config.chat_id)
        self.app: Optional[Application] = None
        self.binance_client: Optional[BinanceClient] = None
        
        # Trading state
        self.is_running = False
        self.active_strategy = None
        self.current_position = None
        
        # Initialize Binance client
        if config.api_key and config.api_secret:
            self.binance_client = BinanceClient(
                config.api_key, 
                config.api_secret, 
                config.use_testnet
            )
            
        # Initialize trading handlers
        self.trading_handlers = TradingHandlers(self)
            
        logger.info(f"Initialized AutoCoin Bot (Testnet: {config.use_testnet})")
        
    def is_authorized(self, update: Update) -> bool:
        """Check if user is authorized"""
        chat_id = str(update.effective_chat.id)
        is_auth = chat_id == self.authorized_chat_id
        
        if not is_auth:
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            
        return is_auth
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        welcome_message = """
🤖 *AutoCoin Bot에 오신 것을 환영합니다!*

비트코인 자동매매 봇이 준비되었습니다.

📋 *사용 가능한 명령어:*
/help - 도움말 보기
/status - 현재 상태 확인
/balance - 계좌 잔고 확인
/strategies - 전략 목록 보기
/run - 자동매매 시작
/stop - 자동매매 중지

⚙️ *현재 설정:*
• 거래소: Binance {'Testnet' if self.config.use_testnet else 'Live'}
• 거래쌍: {self.config.symbol}
• 기본 투자금: {self.config.base_amount} USDT
"""
        
        await update.message.reply_text(
            welcome_message, 
            parse_mode='Markdown'
        )
        logger.info(f"User {update.effective_user.id} started the bot")
        
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        help_text = """
📚 *AutoCoin Bot 도움말*

*기본 명령어:*
• /start - 봇 시작
• /help - 이 도움말 메시지
• /status - 봇 상태 및 현재 포지션

*거래 정보:*
• /balance - 계좌 잔고 확인
• /ticker - 현재 가격 정보
• /position - 현재 포지션 상세

*전략 관리:*
• /strategies - 사용 가능한 전략 목록
• /select [전략명] - 전략 선택
• /params - 현재 전략 파라미터

*자동매매:*
• /run - 자동매매 시작
• /stop - 자동매매 중지
• /pause - 일시정지
• /resume - 재개

*리스크 관리:*
• /sl [퍼센트] - 손절 비율 설정
• /tp [퍼센트] - 익절 비율 설정
• /risk - 리스크 설정 확인

*보고서:*
• /report - 수익률 리포트
• /history - 최근 거래 내역

💡 *팁:* 모든 명령은 인증된 사용자만 사용 가능합니다.
"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
        
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        status_lines = [
            "📊 *AutoCoin Bot 상태*",
            f"",
            f"🤖 봇 상태: {'🟢 실행중' if self.is_running else '🔴 정지'}",
            f"🏦 거래소: Binance {'Testnet' if self.config.use_testnet else 'Live'}",
            f"💱 거래쌍: {self.config.symbol}",
            f"📈 활성 전략: {self.active_strategy or '없음'}",
            f"",
        ]
        
        if self.current_position:
            status_lines.extend([
                "📍 *현재 포지션:*",
                f"• 방향: {self.current_position.get('side', 'N/A')}",
                f"• 진입가: ${self.current_position.get('entry_price', 0):,.2f}",
                f"• 수량: {self.current_position.get('quantity', 0):.8f}",
                f"• 손익: {self.current_position.get('pnl_percentage', 0):.2f}%"
            ])
        else:
            status_lines.append("📍 현재 포지션: 없음")
            
        status_text = "\n".join(status_lines)
        await update.message.reply_text(status_text, parse_mode='Markdown')
        
    async def balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        if not self.binance_client:
            await update.message.reply_text("❌ Binance 클라이언트가 초기화되지 않았습니다.")
            return
            
        try:
            balance = self.binance_client.get_balance()
            
            # Extract relevant balances
            total_balance = balance.get('total', {})
            free_balance = balance.get('free', {})
            used_balance = balance.get('used', {})
            
            balance_text = "💰 *계좌 잔고*\n\n"
            
            # Show major currencies
            currencies = ['USDT', 'BTC', 'ETH', 'BNB']
            
            for currency in currencies:
                total = total_balance.get(currency, 0)
                free = free_balance.get(currency, 0)
                used = used_balance.get(currency, 0)
                
                if total > 0:
                    balance_text += f"*{currency}:*\n"
                    balance_text += f"• 총액: {total:.8f}\n"
                    balance_text += f"• 사용가능: {free:.8f}\n"
                    balance_text += f"• 사용중: {used:.8f}\n\n"
                    
            await update.message.reply_text(balance_text, parse_mode='Markdown')
            logger.info(f"Balance checked for user {update.effective_user.id}")
            
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            await update.message.reply_text(f"❌ 잔고 조회 실패: {str(e)}")
            
    async def ticker(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ticker command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        if not self.binance_client:
            await update.message.reply_text("❌ Binance 클라이언트가 초기화되지 않았습니다.")
            return
            
        try:
            ticker = self.binance_client.get_ticker(self.config.symbol)
            
            ticker_text = f"""
📈 *{self.config.symbol} 현재 시세*

• 현재가: ${ticker.get('last', 0):,.2f}
• 매수호가: ${ticker.get('bid', 0):,.2f}
• 매도호가: ${ticker.get('ask', 0):,.2f}
• 24시간 변동: {ticker.get('percentage', 0):.2f}%
• 24시간 최고: ${ticker.get('high', 0):,.2f}
• 24시간 최저: ${ticker.get('low', 0):,.2f}
• 24시간 거래량: {ticker.get('baseVolume', 0):,.2f}

⏰ 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            await update.message.reply_text(ticker_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Failed to get ticker: {e}")
            await update.message.reply_text(f"❌ 시세 조회 실패: {str(e)}")
            
    async def strategies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /strategies command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        strategies_text = """
📊 *사용 가능한 전략*

1️⃣ *breakout* - 돌파매매 전략
   • 20일 고점 돌파 시 매수
   • 10일 저점 하향 돌파 시 매도
   • 손절: -2%, 익절: +5%

2️⃣ *scalping* - 스캘핑 전략
   • RSI + 볼린저밴드 활용
   • 단기 과매수/과매도 구간 거래
   • 손절: -0.5%, 익절: +1%

3️⃣ *trend* - 추세추종 전략
   • EMA 크로스 시그널
   • 중장기 추세 추종
   • 손절: -3%, Trailing Stop

📌 전략 선택: /select [전략명]
예) /select breakout
"""
        
        await update.message.reply_text(strategies_text, parse_mode='Markdown')
        
    async def run(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /run command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        if self.is_running:
            await update.message.reply_text("⚠️ 이미 자동매매가 실행 중입니다.")
            return
            
        if not self.active_strategy:
            await update.message.reply_text(
                "⚠️ 먼저 전략을 선택해주세요.\n"
                "/strategies - 전략 목록\n"
                "/select [전략명] - 전략 선택"
            )
            return
            
        self.is_running = True
        
        await update.message.reply_text(f"""
✅ *자동매매 시작됨*

• 전략: {self.active_strategy}
• 거래쌍: {self.config.symbol}
• 투자금액: {self.config.base_amount} USDT

⚡️ 실시간 모니터링 중...
중지하려면 /stop 명령을 사용하세요.
""", parse_mode='Markdown')
        
        logger.info(f"Auto trading started with strategy: {self.active_strategy}")
        
    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        if not self.is_running:
            await update.message.reply_text("ℹ️ 자동매매가 실행중이지 않습니다.")
            return
            
        self.is_running = False
        
        await update.message.reply_text("""
🛑 *자동매매 중지됨*

자동매매가 안전하게 중지되었습니다.
다시 시작하려면 /run 명령을 사용하세요.
""", parse_mode='Markdown')
        
        logger.info("Auto trading stopped")
        
    async def select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /select command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        if not context.args:
            await update.message.reply_text(
                "⚠️ 전략 이름을 입력해주세요.\n"
                "예) /select breakout"
            )
            return
            
        strategy_name = context.args[0].lower()
        available_strategies = ['breakout', 'scalping', 'trend']
        
        if strategy_name not in available_strategies:
            await update.message.reply_text(
                f"❌ 잘못된 전략명입니다.\n"
                f"사용 가능한 전략: {', '.join(available_strategies)}"
            )
            return
            
        self.active_strategy = strategy_name
        
        await update.message.reply_text(f"""
✅ *전략 선택됨*

선택된 전략: {strategy_name}

자동매매를 시작하려면 /run 명령을 사용하세요.
""", parse_mode='Markdown')
        
        logger.info(f"Strategy selected: {strategy_name}")
        
    async def unknown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown commands"""
        if not self.is_authorized(update):
            return
            
        await update.message.reply_text(
            "❓ 알 수 없는 명령어입니다.\n"
            "/help 명령으로 사용 가능한 명령어를 확인하세요."
        )
        
    async def setup_commands(self):
        """Set bot commands in Telegram"""
        commands = [
            BotCommand("start", "봇 시작"),
            BotCommand("help", "도움말"),
            BotCommand("status", "현재 상태"),
            BotCommand("balance", "계좌 잔고"),
            BotCommand("ticker", "현재 시세"),
            BotCommand("strategies", "전략 목록"),
            BotCommand("select", "전략 선택"),
            BotCommand("run", "자동매매 시작"),
            BotCommand("stop", "자동매매 중지"),
            BotCommand("report", "수익률 리포트"),
        ]
        
        await self.app.bot.set_my_commands(commands)
        logger.info("Bot commands set up")
        
    def setup_handlers(self):
        """Set up command handlers"""
        if not self.app:
            raise ValueError("Application not initialized")
            
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help))
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CommandHandler("balance", self.balance))
        self.app.add_handler(CommandHandler("ticker", self.ticker))
        self.app.add_handler(CommandHandler("strategies", self.strategies))
        self.app.add_handler(CommandHandler("select", self.select))
        self.app.add_handler(CommandHandler("run", self.run))
        self.app.add_handler(CommandHandler("stop", self.stop))
        
        # Trading handlers
        self.app.add_handler(CommandHandler("sl", self.trading_handlers.set_stop_loss))
        self.app.add_handler(CommandHandler("tp", self.trading_handlers.set_take_profit))
        self.app.add_handler(CommandHandler("risk", self.trading_handlers.show_risk_settings))
        self.app.add_handler(CommandHandler("position", self.trading_handlers.show_position))
        self.app.add_handler(CommandHandler("report", self.trading_handlers.show_report))
        self.app.add_handler(CommandHandler("history", self.trading_handlers.show_history))
        self.app.add_handler(CommandHandler("pause", self.trading_handlers.pause_trading))
        self.app.add_handler(CommandHandler("resume", self.trading_handlers.resume_trading))
        self.app.add_handler(CommandHandler("params", self.trading_handlers.show_params))
        
        # Unknown command handler
        self.app.add_handler(MessageHandler(filters.COMMAND, self.unknown))
        
        logger.info("Command handlers set up")
        
    async def post_init(self, application: Application):
        """Post initialization hook"""
        await self.setup_commands()
        logger.info("Bot post initialization completed")
        
    def run(self):
        """Run the bot"""
        # Create application
        self.app = Application.builder().token(self.token).post_init(self.post_init).build()
        
        # Setup handlers
        self.setup_handlers()
        
        # Run the bot
        logger.info("Starting Telegram bot...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    async def send_message(self, text: str, parse_mode: str = 'Markdown'):
        """Send message to authorized user"""
        if self.app and self.authorized_chat_id:
            try:
                await self.app.bot.send_message(
                    chat_id=self.authorized_chat_id,
                    text=text,
                    parse_mode=parse_mode
                )
            except Exception as e:
                logger.error(f"Failed to send message: {e}")