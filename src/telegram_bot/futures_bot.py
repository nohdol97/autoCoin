"""
Extended Telegram Bot with Futures Trading Support
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import logging
from typing import Optional, Dict, Any, List
import asyncio
from datetime import datetime

from ..config import Config
from ..exchange.binance_futures_client import BinanceFuturesClient
from ..trading.futures_position_manager import FuturesPositionManager
from ..trading.futures_types import PositionSide, MarginMode
from ..utils.risk_manager import RiskManager
from ..logger import get_logger
from .bot import AutoCoinBot

logger = get_logger('futures_telegram_bot')


class AutoCoinFuturesBot(AutoCoinBot):
    """Extended Telegram Bot with futures trading capabilities"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        
        # Initialize futures client
        self.futures_client: Optional[BinanceFuturesClient] = None
        self.position_manager: Optional[FuturesPositionManager] = None
        
        if config.api_key and config.api_secret:
            self.futures_client = BinanceFuturesClient(
                config.api_key,
                config.api_secret,
                config.use_testnet
            )
            
            # Initialize position manager
            risk_manager = RiskManager(config.risk_percentage)
            self.position_manager = FuturesPositionManager(
                self.futures_client,
                risk_manager
            )
            
        # Futures-specific state
        self.futures_strategies = [
            'funding_arbitrage',
            'grid_trading', 
            'long_short_switching',
            'volatility_breakout'
        ]
        self.active_futures_strategy = None
        self.default_leverage = 5
        
        logger.info(f"Initialized Futures Bot (Testnet: {config.use_testnet})")
        
    async def initialize(self):
        """Initialize futures components"""
        if self.futures_client:
            await self.futures_client.initialize()
            await self.position_manager.initialize()
            
    async def futures_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /futures_help command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        help_text = """
📚 *AutoCoin Futures 도움말*

*선물 거래 명령어:*
• /futures_status - 선물 계정 상태
• /futures_balance - 선물 계좌 잔고
• /futures_positions - 현재 포지션 목록
• /futures_pnl - 손익 현황

*포지션 관리:*
• /futures_open [long/short] [size] - 포지션 열기
• /futures_close [symbol] [percentage] - 포지션 닫기
• /futures_leverage [1-20] - 레버리지 설정
• /futures_sl [price] - 손절가 설정
• /futures_tp [price] - 익절가 설정

*선물 전략:*
• /futures_strategies - 선물 전략 목록
• /futures_select [전략명] - 선물 전략 선택
• /futures_run - 선물 자동매매 시작
• /futures_stop - 선물 자동매매 중지

*펀딩 & 리스크:*
• /funding_rate [symbol] - 펀딩 비율 확인
• /liquidation_risk - 청산 위험도 확인
• /futures_risk - 전체 리스크 메트릭

*긴급 명령:*
• /futures_emergency_close - 모든 포지션 긴급 청산

⚠️ *주의:* 선물 거래는 높은 위험을 동반합니다.
"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
        
    async def futures_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /futures_status command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        try:
            # Update positions
            await self.position_manager.update_positions()
            
            # Get risk metrics
            risk_metrics = await self.position_manager.get_risk_metrics()
            
            # Get position summary
            position_summary = self.position_manager.get_position_summary()
            
            status_text = f"""
📊 *선물 거래 상태*

*계정 정보:*
• 총 마진: ${risk_metrics.total_margin:,.2f}
• 사용 가능 마진: ${risk_metrics.free_margin:,.2f}
• 마진 사용률: {risk_metrics.margin_usage_percentage:.1f}%
• 마진 레벨: {risk_metrics.margin_level:.1f}%

*포지션 현황:*
• 오픈 포지션: {position_summary['count']}개
• 총 명목가치: ${position_summary['total_notional']:,.2f}
• 미실현 손익: ${position_summary['total_pnl']:,.2f}
• 손익률: {position_summary['total_pnl_percentage']:.2f}%

*리스크 상태:*
• 현재 레버리지: {risk_metrics.current_leverage}x
• 최대 레버리지: {risk_metrics.max_leverage}x
• 과도한 레버리지: {'⚠️ 예' if risk_metrics.is_overleveraged else '✅ 아니오'}

*일일 성과:*
• 일일 손익: ${risk_metrics.daily_pnl:,.2f}
• 주간 손익: ${risk_metrics.weekly_pnl:,.2f}
"""
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Failed to get futures status: {e}")
            await update.message.reply_text(f"❌ 상태 조회 실패: {str(e)}")
            
    async def futures_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /futures_positions command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        try:
            await self.position_manager.update_positions()
            
            if not self.position_manager.positions:
                await update.message.reply_text("📍 현재 오픈된 포지션이 없습니다.")
                return
                
            positions_text = "📍 *현재 포지션*\n\n"
            
            for symbol, position in self.position_manager.positions.items():
                emoji = "📈" if position.side == PositionSide.LONG else "📉"
                
                positions_text += f"{emoji} *{symbol}*\n"
                positions_text += f"• 방향: {position.side.value.upper()}\n"
                positions_text += f"• 수량: {position.contracts}\n"
                positions_text += f"• 진입가: ${position.entry_price:,.2f}\n"
                positions_text += f"• 현재가: ${position.mark_price:,.2f}\n"
                positions_text += f"• 미실현 손익: ${position.unrealized_pnl:,.2f}\n"
                positions_text += f"• 손익률: {position.pnl_percentage:.2f}%\n"
                positions_text += f"• 레버리지: {position.leverage}x\n"
                positions_text += f"• 청산가: ${position.liquidation_price:,.2f}\n\n"
                
            await update.message.reply_text(positions_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            await update.message.reply_text(f"❌ 포지션 조회 실패: {str(e)}")
            
    async def futures_open(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /futures_open command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        if len(context.args) < 2:
            await update.message.reply_text(
                "⚠️ 사용법: /futures_open [long/short] [size_usdt]\n"
                "예) /futures_open long 100"
            )
            return
            
        try:
            direction = context.args[0].lower()
            size_usdt = float(context.args[1])
            
            if direction not in ['long', 'short']:
                await update.message.reply_text("❌ 방향은 long 또는 short여야 합니다.")
                return
                
            # Get current price
            ticker = await asyncio.to_thread(
                self.futures_client.get_futures_ticker,
                self.config.symbol
            )
            current_price = ticker['last']
            
            # Calculate position size
            position_size = await asyncio.to_thread(
                self.futures_client.calculate_futures_position_size,
                self.config.symbol,
                size_usdt,
                self.default_leverage,
                current_price
            )
            
            # Open position
            result = await self.position_manager.open_position(
                symbol=self.config.symbol,
                side='buy' if direction == 'long' else 'sell',
                size=position_size,
                leverage=self.default_leverage
            )
            
            if result.get('status') == 'error':
                await update.message.reply_text(f"❌ 포지션 오픈 실패: {result['message']}")
            else:
                await update.message.reply_text(f"""
✅ *포지션 오픈됨*

• 방향: {direction.upper()}
• 수량: {position_size}
• 레버리지: {self.default_leverage}x
• 진입가: ${current_price:,.2f}
• 명목가치: ${size_usdt * self.default_leverage:,.2f}

포지션 확인: /futures_positions
""", parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Failed to open position: {e}")
            await update.message.reply_text(f"❌ 포지션 오픈 실패: {str(e)}")
            
    async def futures_close(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /futures_close command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        symbol = self.config.symbol
        percentage = 100  # Default to close 100%
        
        if context.args:
            if len(context.args) >= 2:
                symbol = context.args[0]
                percentage = float(context.args[1])
            else:
                percentage = float(context.args[0])
                
        try:
            result = await self.position_manager.close_position(symbol, percentage)
            
            if result.get('status') == 'error':
                await update.message.reply_text(f"❌ 포지션 종료 실패: {result['message']}")
            else:
                await update.message.reply_text(f"""
✅ *포지션 종료됨*

• 심볼: {symbol}
• 종료 비율: {percentage}%

남은 포지션 확인: /futures_positions
""", parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            await update.message.reply_text(f"❌ 포지션 종료 실패: {str(e)}")
            
    async def futures_leverage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /futures_leverage command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        if not context.args:
            await update.message.reply_text(
                f"현재 기본 레버리지: {self.default_leverage}x\n"
                f"변경: /futures_leverage [1-20]"
            )
            return
            
        try:
            new_leverage = int(context.args[0])
            
            if not 1 <= new_leverage <= 20:
                await update.message.reply_text("❌ 레버리지는 1-20 사이여야 합니다.")
                return
                
            self.default_leverage = new_leverage
            
            # Update leverage for open positions
            for symbol in self.position_manager.positions:
                await self.position_manager.adjust_leverage(symbol, new_leverage)
                
            await update.message.reply_text(f"""
✅ *레버리지 변경됨*

새 레버리지: {new_leverage}x

⚠️ 높은 레버리지는 높은 위험을 동반합니다.
""", parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Failed to set leverage: {e}")
            await update.message.reply_text(f"❌ 레버리지 설정 실패: {str(e)}")
            
    async def futures_strategies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /futures_strategies command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        strategies_text = """
📊 *선물 거래 전략*

1️⃣ *funding_arbitrage* - 펀딩비 차익거래
   • 펀딩비가 높을 때 반대 포지션
   • 현물 헤지로 리스크 최소화
   • 안정적인 수익 추구

2️⃣ *grid_trading* - 그리드 매매
   • 일정 간격으로 매수/매도 주문
   • 변동성 장세에서 수익
   • 자동 리밸런싱

3️⃣ *long_short_switching* - 롱숏 전환
   • 추세에 따라 방향 전환
   • 멀티 타임프레임 분석
   • 트레일링 스탑 적용

4️⃣ *volatility_breakout* - 변동성 돌파
   • 볼린저밴드 수축 후 돌파
   • 높은 레버리지로 단기 수익
   • 타이트한 손절 관리

📌 전략 선택: /futures_select [전략명]
"""
        
        await update.message.reply_text(strategies_text, parse_mode='Markdown')
        
    async def funding_rate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /funding_rate command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        symbol = self.config.symbol
        if context.args:
            symbol = context.args[0]
            
        try:
            funding = await self.position_manager.get_funding_rate(symbol)
            
            if not funding:
                await update.message.reply_text("❌ 펀딩비 정보를 가져올 수 없습니다.")
                return
                
            funding_text = f"""
💰 *{symbol} 펀딩비 정보*

• 현재 펀딩비: {funding.rate:.4%}
• 연간 환산: {funding.annual_rate:.2f}%
• 다음 펀딩 시간: {funding.next_funding_time.strftime('%H:%M')}
• 남은 시간: {funding.hours_until_funding:.1f}시간

📊 펀딩비 해석:
"""
            
            if funding.rate > 0:
                funding_text += "• 양수 (+): 롱 포지션이 숏에게 지불\n"
                funding_text += "• 추천: 숏 포지션 고려"
            else:
                funding_text += "• 음수 (-): 숏 포지션이 롱에게 지불\n"
                funding_text += "• 추천: 롱 포지션 고려"
                
            await update.message.reply_text(funding_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Failed to get funding rate: {e}")
            await update.message.reply_text(f"❌ 펀딩비 조회 실패: {str(e)}")
            
    async def liquidation_risk(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /liquidation_risk command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        try:
            at_risk = await self.position_manager.check_liquidation_risk()
            
            if not at_risk:
                await update.message.reply_text("✅ 청산 위험이 있는 포지션이 없습니다.")
                return
                
            risk_text = "⚠️ *청산 위험 포지션*\n\n"
            
            for position in at_risk:
                emoji = "🔴" if position['risk_level'] == 'HIGH' else "🟡"
                
                risk_text += f"{emoji} *{position['symbol']}*\n"
                risk_text += f"• 방향: {position['side']}\n"
                risk_text += f"• 현재가: ${position['mark_price']:,.2f}\n"
                risk_text += f"• 청산가: ${position['liquidation_price']:,.2f}\n"
                risk_text += f"• 거리: {position['distance_percentage']:.2f}%\n\n"
                
            risk_text += "⚠️ 즉시 리스크 관리가 필요합니다!"
            
            await update.message.reply_text(risk_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Failed to check liquidation risk: {e}")
            await update.message.reply_text(f"❌ 청산 위험 확인 실패: {str(e)}")
            
    async def futures_emergency_close(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /futures_emergency_close command"""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ 확인", callback_data='confirm_emergency_close'),
                InlineKeyboardButton("❌ 취소", callback_data='cancel_emergency_close')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚠️ *긴급 청산 확인*\n\n"
            "모든 선물 포지션을 즉시 청산합니다.\n"
            "이 작업은 되돌릴 수 없습니다.\n\n"
            "계속하시겠습니까?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    async def handle_emergency_close_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle emergency close confirmation"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'confirm_emergency_close':
            try:
                results = await self.position_manager.emergency_close_all()
                
                closed_count = sum(1 for r in results if r['status'] == 'closed')
                failed_count = sum(1 for r in results if r['status'] == 'error')
                
                result_text = f"""
🚨 *긴급 청산 완료*

• 성공: {closed_count}개
• 실패: {failed_count}개

상세 내역:
"""
                
                for result in results:
                    if result['status'] == 'closed':
                        result_text += f"✅ {result['symbol']} - 청산됨\n"
                    else:
                        result_text += f"❌ {result['symbol']} - 실패: {result['error']}\n"
                        
                await query.edit_message_text(result_text, parse_mode='Markdown')
                
            except Exception as e:
                logger.error(f"Emergency close failed: {e}")
                await query.edit_message_text(f"❌ 긴급 청산 실패: {str(e)}")
                
        else:  # cancelled
            await query.edit_message_text("❌ 긴급 청산이 취소되었습니다.")
            
    def setup_futures_handlers(self, app: Application):
        """Setup futures-specific command handlers"""
        # Futures commands
        app.add_handler(CommandHandler("futures_help", self.futures_help))
        app.add_handler(CommandHandler("futures_status", self.futures_status))
        app.add_handler(CommandHandler("futures_positions", self.futures_positions))
        app.add_handler(CommandHandler("futures_open", self.futures_open))
        app.add_handler(CommandHandler("futures_close", self.futures_close))
        app.add_handler(CommandHandler("futures_leverage", self.futures_leverage))
        app.add_handler(CommandHandler("futures_strategies", self.futures_strategies))
        app.add_handler(CommandHandler("funding_rate", self.funding_rate))
        app.add_handler(CommandHandler("liquidation_risk", self.liquidation_risk))
        app.add_handler(CommandHandler("futures_emergency_close", self.futures_emergency_close))
        
        # Callback query handler for emergency close
        app.add_handler(CallbackQueryHandler(
            self.handle_emergency_close_callback,
            pattern='^(confirm|cancel)_emergency_close$'
        ))
        
        logger.info("Futures command handlers registered")