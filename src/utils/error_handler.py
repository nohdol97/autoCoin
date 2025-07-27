import logging
import traceback
from typing import Optional, Callable, Any
from datetime import datetime

from src.exceptions import (
    APIException, RateLimitException, NetworkException,
    TradingException, InsufficientBalanceException,
    SystemException
)


class ErrorHandler:
    """중앙 집중식 에러 처리"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_callbacks = {}
        self.error_history = []
        
    def register_callback(self, exception_type: type, callback: Callable):
        """특정 예외 타입에 대한 콜백 등록"""
        self.error_callbacks[exception_type] = callback
        
    async def handle_error(self, error: Exception, context: dict = None) -> bool:
        """
        에러를 처리하고 적절한 조치를 취함
        
        Returns:
            bool: 에러가 성공적으로 처리되었는지 여부
        """
        context = context or {}
        
        # 에러 정보 기록
        error_info = {
            'timestamp': datetime.now(),
            'type': type(error).__name__,
            'message': str(error),
            'context': context,
            'traceback': traceback.format_exc()
        }
        self.error_history.append(error_info)
        
        # 로깅
        self.logger.error(f"{error_info['type']}: {error_info['message']}")
        if context:
            self.logger.error(f"Context: {context}")
            
        # 에러 타입별 처리
        handled = await self._handle_specific_error(error, context)
        
        # 콜백 실행
        for exc_type, callback in self.error_callbacks.items():
            if isinstance(error, exc_type):
                try:
                    await callback(error, context)
                except Exception as cb_error:
                    self.logger.error(f"Error in callback: {cb_error}")
                    
        return handled
        
    async def _handle_specific_error(self, error: Exception, context: dict) -> bool:
        """에러 타입별 특수 처리"""
        
        # Rate Limit 에러
        if isinstance(error, RateLimitException):
            retry_after = error.retry_after or 60
            self.logger.warning(f"Rate limit exceeded. Waiting {retry_after} seconds...")
            return True
            
        # 네트워크 에러
        elif isinstance(error, NetworkException):
            self.logger.warning("Network error detected. Will retry connection...")
            return True
            
        # 잔고 부족
        elif isinstance(error, InsufficientBalanceException):
            self.logger.error(f"Insufficient balance: {error.details}")
            # 거래 중단 필요
            return False
            
        # API 에러
        elif isinstance(error, APIException):
            self.logger.error(f"API error: {error.code} - {error.message}")
            return False
            
        # 거래 에러
        elif isinstance(error, TradingException):
            self.logger.error(f"Trading error: {error.code} - {error.message}")
            return False
            
        # 시스템 에러
        elif isinstance(error, SystemException):
            self.logger.critical(f"System error: {error.code} - {error.message}")
            # 시스템 종료 필요할 수 있음
            return False
            
        # 기타 예외
        else:
            self.logger.exception(f"Unexpected error: {error}")
            return False
            
    def get_error_summary(self, hours: int = 24) -> dict:
        """최근 N시간 동안의 에러 요약"""
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_errors = [
            e for e in self.error_history 
            if e['timestamp'] > cutoff_time
        ]
        
        # 에러 타입별 집계
        error_counts = {}
        for error in recent_errors:
            error_type = error['type']
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
            
        return {
            'total_errors': len(recent_errors),
            'error_counts': error_counts,
            'most_recent': recent_errors[-1] if recent_errors else None
        }
        
    def clear_old_errors(self, days: int = 7):
        """오래된 에러 기록 삭제"""
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(days=days)
        
        self.error_history = [
            e for e in self.error_history 
            if e['timestamp'] > cutoff_time
        ]