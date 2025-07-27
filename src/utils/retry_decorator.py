import asyncio
import functools
import logging
from typing import Callable, Union, Tuple, Type

from src.exceptions import NetworkException, RateLimitException


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: logging.Logger = None
) -> Callable:
    """
    에러 발생 시 재시도하는 데코레이터
    
    Args:
        max_retries: 최대 재시도 횟수
        delay: 초기 대기 시간 (초)
        backoff: 백오프 배수 (각 재시도마다 대기 시간이 이 배수만큼 증가)
        exceptions: 재시도할 예외 타입들
        logger: 로거 인스턴스
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            _logger = logger or logging.getLogger(func.__module__)
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                    
                except exceptions as e:
                    if attempt == max_retries - 1:
                        _logger.error(f"{func.__name__} failed after {max_retries} attempts")
                        raise
                        
                    # Rate Limit 예외는 특별 처리
                    if isinstance(e, RateLimitException) and hasattr(e, 'retry_after'):
                        wait_time = e.retry_after
                    else:
                        wait_time = current_delay
                        
                    _logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {wait_time}s... Error: {str(e)}"
                    )
                    
                    await asyncio.sleep(wait_time)
                    current_delay *= backoff
                    
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            _logger = logger or logging.getLogger(func.__module__)
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    if attempt == max_retries - 1:
                        _logger.error(f"{func.__name__} failed after {max_retries} attempts")
                        raise
                        
                    wait_time = current_delay
                    _logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {wait_time}s... Error: {str(e)}"
                    )
                    
                    import time
                    time.sleep(wait_time)
                    current_delay *= backoff
                    
        # 비동기 함수인지 확인
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


# 일반적인 사용 케이스를 위한 사전 정의된 데코레이터
retry_on_network_error = retry_on_error(
    max_retries=5,
    delay=1.0,
    backoff=2.0,
    exceptions=(NetworkException, ConnectionError, TimeoutError)
)

retry_on_api_error = retry_on_error(
    max_retries=3,
    delay=2.0,
    backoff=3.0,
    exceptions=(RateLimitException, NetworkException)
)