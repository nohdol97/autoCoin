class TradingException(Exception):
    """거래 관련 기본 예외"""
    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class InsufficientBalanceException(TradingException):
    """잔고 부족"""
    def __init__(self, required_amount: float, available_amount: float):
        message = f"Insufficient balance. Required: {required_amount}, Available: {available_amount}"
        super().__init__(message, code="INSUFFICIENT_BALANCE")
        self.details = {
            'required_amount': required_amount,
            'available_amount': available_amount
        }


class InvalidOrderException(TradingException):
    """잘못된 주문"""
    def __init__(self, message: str, order_details: dict = None):
        super().__init__(message, code="INVALID_ORDER")
        if order_details:
            self.details['order'] = order_details


class PositionNotFoundException(TradingException):
    """포지션을 찾을 수 없음"""
    def __init__(self, position_id: str = None):
        message = f"Position not found: {position_id}" if position_id else "No active position found"
        super().__init__(message, code="POSITION_NOT_FOUND")
        if position_id:
            self.details['position_id'] = position_id


class StrategyException(TradingException):
    """전략 실행 오류"""
    def __init__(self, strategy_name: str, message: str):
        full_message = f"Strategy '{strategy_name}' error: {message}"
        super().__init__(full_message, code="STRATEGY_ERROR")
        self.details['strategy_name'] = strategy_name