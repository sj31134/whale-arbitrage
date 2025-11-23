"""
재시도 로직 유틸리티
지수 백오프를 사용한 재시도 데코레이터 및 함수
"""

import time
import functools
from typing import Callable, Any, Type, Tuple
from src.utils.logger import logger

def retry_with_backoff(
    max_attempts: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    지수 백오프를 사용한 재시도 데코레이터
    
    Parameters:
    -----------
    max_attempts : int
        최대 재시도 횟수 (기본값: 5)
    base_delay : float
        초기 대기 시간 (초, 기본값: 1.0)
    max_delay : float
        최대 대기 시간 (초, 기본값: 60.0)
    exponential_base : float
        지수 백오프 베이스 (기본값: 2.0)
    exceptions : Tuple[Type[Exception], ...]
        재시도할 예외 타입 (기본값: 모든 예외)
    
    Returns:
    --------
    Callable : 데코레이터 함수
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        # 지수 백오프 계산
                        delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                        
                        logger.warning(
                            f"⚠️ {func.__name__} 실패 (시도 {attempt}/{max_attempts}): {e}"
                        )
                        logger.info(f"   {delay:.1f}초 후 재시도...")
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"❌ {func.__name__} 최대 재시도 횟수 초과 ({max_attempts}회)"
                        )
                        raise
            
            # 모든 재시도 실패
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator


def retry_on_http_error(
    max_attempts: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retry_status_codes: Tuple[int, ...] = (500, 502, 503, 504)
):
    """
    HTTP 에러 발생 시 재시도하는 데코레이터 (특히 502 Bad Gateway 등)
    
    Parameters:
    -----------
    max_attempts : int
        최대 재시도 횟수 (기본값: 5)
    base_delay : float
        초기 대기 시간 (초, 기본값: 1.0)
    max_delay : float
        최대 대기 시간 (초, 기본값: 60.0)
    exponential_base : float
        지수 백오프 베이스 (기본값: 2.0)
    retry_status_codes : Tuple[int, ...]
        재시도할 HTTP 상태 코드 (기본값: 500, 502, 503, 504)
    
    Returns:
    --------
    Callable : 데코레이터 함수
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import requests
            
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.HTTPError as e:
                    last_exception = e
                    
                    status_code = e.response.status_code if hasattr(e, 'response') else None
                    
                    if status_code in retry_status_codes and attempt < max_attempts:
                        # 지수 백오프 계산
                        delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                        
                        logger.warning(
                            f"⚠️ {func.__name__} HTTP {status_code} 에러 (시도 {attempt}/{max_attempts})"
                        )
                        logger.info(f"   {delay:.1f}초 후 재시도...")
                        time.sleep(delay)
                    else:
                        # 재시도하지 않을 에러이거나 최대 재시도 횟수 초과
                        if attempt >= max_attempts:
                            logger.error(
                                f"❌ {func.__name__} 최대 재시도 횟수 초과 ({max_attempts}회)"
                            )
                        raise
                except Exception as e:
                    # HTTP 에러가 아닌 경우 즉시 재발
                    raise
            
            # 모든 재시도 실패
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator
