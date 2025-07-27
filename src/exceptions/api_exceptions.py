class APIException(Exception):
    """API 관련 기본 예외"""
    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class RateLimitException(APIException):
    """API Rate Limit 초과"""
    def __init__(self, message: str = "API rate limit exceeded", retry_after: int = None):
        super().__init__(message, code="RATE_LIMIT")
        self.retry_after = retry_after
        if retry_after:
            self.details['retry_after'] = retry_after


class NetworkException(APIException):
    """네트워크 연결 오류"""
    def __init__(self, message: str = "Network connection error", original_error: Exception = None):
        super().__init__(message, code="NETWORK_ERROR")
        if original_error:
            self.details['original_error'] = str(original_error)


class AuthenticationException(APIException):
    """인증 오류"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code="AUTH_FAILED")