from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import re
from typing import Dict, Any

from ..logger import get_logger

logger = get_logger('telegram_handlers')

# Conversation states
WAITING_FOR_SL = 1
WAITING_FOR_TP = 2

class TradingHandlers:
    """Additional trading-related handlers"""
    
    def __init__(self, bot):
        self.bot = bot
        
    async def set_stop_loss(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sl command"""
        if not self.bot.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        if not context.args:
            await update.message.reply_text(
                "📝 손절 비율을 입력해주세요.\n"
                "예) /sl 2.5 (2.5% 손절)"
            )
            return ConversationHandler.END
            
        try:
            sl_percent = float(context.args[0])
            
            if sl_percent <= 0 or sl_percent > 50:
                await update.message.reply_text("⚠️ 손절 비율은 0-50% 사이여야 합니다.")
                return
                
            # Update strategy config
            if self.bot.active_strategy and self.bot.config.strategies.get(self.bot.active_strategy):
                self.bot.config.strategies[self.bot.active_strategy]['stop_loss'] = sl_percent
                
                await update.message.reply_text(f"""
✅ *손절 설정 완료*

• 전략: {self.bot.active_strategy}
• 손절 비율: -{sl_percent}%

⚠️ 실행 중인 포지션에는 적용되지 않습니다.
새로운 포지션부터 적용됩니다.
""", parse_mode='Markdown')
                
                logger.info(f"Stop loss set to {sl_percent}% for strategy {self.bot.active_strategy}")
            else:
                await update.message.reply_text("⚠️ 먼저 전략을 선택해주세요.")
                
        except ValueError:
            await update.message.reply_text("❌ 올바른 숫자를 입력해주세요.")
            
    async def set_take_profit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tp command"""
        if not self.bot.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        if not context.args:
            await update.message.reply_text(
                "📝 익절 비율을 입력해주세요.\n"
                "예) /tp 5.0 (5% 익절)"
            )
            return
            
        try:
            tp_percent = float(context.args[0])
            
            if tp_percent <= 0 or tp_percent > 100:
                await update.message.reply_text("⚠️ 익절 비율은 0-100% 사이여야 합니다.")
                return
                
            # Update strategy config
            if self.bot.active_strategy and self.bot.config.strategies.get(self.bot.active_strategy):
                self.bot.config.strategies[self.bot.active_strategy]['take_profit'] = tp_percent
                
                await update.message.reply_text(f"""
✅ *익절 설정 완료*

• 전략: {self.bot.active_strategy}
• 익절 비율: +{tp_percent}%

⚠️ 실행 중인 포지션에는 적용되지 않습니다.
새로운 포지션부터 적용됩니다.
""", parse_mode='Markdown')
                
                logger.info(f"Take profit set to {tp_percent}% for strategy {self.bot.active_strategy}")
            else:
                await update.message.reply_text("⚠️ 먼저 전략을 선택해주세요.")
                
        except ValueError:
            await update.message.reply_text("❌ 올바른 숫자를 입력해주세요.")
            
    async def show_risk_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /risk command"""
        if not self.bot.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        if not self.bot.active_strategy:
            await update.message.reply_text("⚠️ 활성화된 전략이 없습니다.")
            return
            
        strategy_config = self.bot.config.strategies.get(self.bot.active_strategy, {})
        
        risk_text = f"""
⚖️ *리스크 관리 설정*

• 활성 전략: {self.bot.active_strategy}
• 손절 비율: -{strategy_config.get('stop_loss', 2.0)}%
• 익절 비율: +{strategy_config.get('take_profit', 5.0)}%
• 최대 포지션: {self.bot.config.max_positions}개
• 투자 금액: {self.bot.config.base_amount} USDT

💡 변경 명령:
• /sl [퍼센트] - 손절 설정
• /tp [퍼센트] - 익절 설정
"""
        
        await update.message.reply_text(risk_text, parse_mode='Markdown')
        
    async def show_position(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /position command"""
        if not self.bot.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        if not self.bot.current_position:
            await update.message.reply_text("📍 현재 보유 중인 포지션이 없습니다.")
            return
            
        pos = self.bot.current_position
        
        position_text = f"""
📍 *현재 포지션 상세*

• 전략: {pos.get('strategy', 'N/A')}
• 방향: {'🟢 매수' if pos.get('side') == 'LONG' else '🔴 매도'}
• 진입가: ${pos.get('entry_price', 0):,.2f}
• 현재가: ${pos.get('current_price', 0):,.2f}
• 수량: {pos.get('quantity', 0):.8f} BTC
• 가치: ${pos.get('value', 0):,.2f}

💰 *손익 현황:*
• 손익: ${pos.get('pnl', 0):,.2f}
• 수익률: {pos.get('pnl_percentage', 0):.2f}%

🎯 *목표가:*
• 손절가: ${pos.get('stop_loss', 0):,.2f}
• 익절가: ${pos.get('take_profit', 0):,.2f}

⏰ 진입 시간: {pos.get('entry_time', 'N/A')}
"""
        
        await update.message.reply_text(position_text, parse_mode='Markdown')
        
    async def show_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /report command"""
        if not self.bot.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        # This would normally fetch from database/storage
        report_text = """
📊 *수익률 리포트*

📅 *일일 성과:*
• 거래 횟수: 0
• 승률: 0%
• 손익: $0.00 (0.00%)

📅 *주간 성과:*
• 거래 횟수: 0
• 승률: 0%
• 손익: $0.00 (0.00%)

📅 *월간 성과:*
• 거래 횟수: 0
• 승률: 0%
• 손익: $0.00 (0.00%)

📈 *전체 통계:*
• 총 거래: 0
• 승/패: 0/0
• 최대 수익: $0.00
• 최대 손실: $0.00
• 총 손익: $0.00 (0.00%)

⚠️ 거래 내역이 없습니다.
"""
        
        await update.message.reply_text(report_text, parse_mode='Markdown')
        
    async def show_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /history command"""
        if not self.bot.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        # This would normally fetch from database/storage
        history_text = """
📜 *최근 거래 내역*

아직 거래 내역이 없습니다.

자동매매를 시작하려면:
1. /strategies - 전략 확인
2. /select [전략명] - 전략 선택
3. /run - 자동매매 시작
"""
        
        await update.message.reply_text(history_text, parse_mode='Markdown')
        
    async def pause_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pause command"""
        if not self.bot.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        if not self.bot.is_running:
            await update.message.reply_text("ℹ️ 자동매매가 실행중이지 않습니다.")
            return
            
        # In real implementation, would pause the trading loop
        await update.message.reply_text("""
⏸ *자동매매 일시정지*

자동매매가 일시정지되었습니다.
현재 포지션은 유지됩니다.

다시 시작하려면 /resume 명령을 사용하세요.
""", parse_mode='Markdown')
        
        logger.info("Trading paused")
        
    async def resume_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /resume command"""
        if not self.bot.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        if not self.bot.is_running:
            await update.message.reply_text("ℹ️ 자동매매가 실행중이지 않습니다.")
            return
            
        await update.message.reply_text("""
▶️ *자동매매 재개*

자동매매가 다시 시작되었습니다.
""", parse_mode='Markdown')
        
        logger.info("Trading resumed")
        
    async def show_params(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /params command"""
        if not self.bot.is_authorized(update):
            await update.message.reply_text("⛔ 인증되지 않은 사용자입니다.")
            return
            
        if not self.bot.active_strategy:
            await update.message.reply_text("⚠️ 활성화된 전략이 없습니다.")
            return
            
        strategy_config = self.bot.config.strategies.get(self.bot.active_strategy, {})
        
        params_text = f"⚙️ *{self.bot.active_strategy} 전략 파라미터*\n\n"
        
        # Format parameters based on strategy
        if self.bot.active_strategy == 'breakout':
            params_text += f"""
• 매수 관찰 기간: {strategy_config.get('lookback_buy', 20)}일
• 매도 관찰 기간: {strategy_config.get('lookback_sell', 10)}일
• 손절: -{strategy_config.get('stop_loss', 2.0)}%
• 익절: +{strategy_config.get('take_profit', 5.0)}%
"""
        elif self.bot.active_strategy == 'scalping':
            params_text += f"""
• RSI 기간: {strategy_config.get('rsi_period', 14)}
• RSI 과매도: {strategy_config.get('rsi_oversold', 30)}
• RSI 과매수: {strategy_config.get('rsi_overbought', 70)}
• 볼린저밴드 기간: {strategy_config.get('bb_period', 20)}
• 볼린저밴드 표준편차: {strategy_config.get('bb_std', 2)}
• 손절: -{strategy_config.get('stop_loss', 0.5)}%
• 익절: +{strategy_config.get('take_profit', 1.0)}%
"""
        elif self.bot.active_strategy == 'trend':
            params_text += f"""
• 단기 EMA: {strategy_config.get('ema_fast', 12)}
• 장기 EMA: {strategy_config.get('ema_slow', 26)}
• 손절: -{strategy_config.get('stop_loss', 3.0)}%
• Trailing Stop: {strategy_config.get('trailing_stop', 3.0)}%
"""
        
        await update.message.reply_text(params_text, parse_mode='Markdown')