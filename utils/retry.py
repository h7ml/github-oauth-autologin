"""重试装饰器和工具"""
import time
import logging
from functools import wraps
from typing import Callable, TypeVar, Any, Type, Tuple
from requests.exceptions import RequestException
from playwright.sync_api import TimeoutError as PlaywrightTimeout, Error as PlaywrightError

from core.constants import RetryConfig

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry(
    max_attempts: int = RetryConfig.MAX_ATTEMPTS,
    delay: float = RetryConfig.INITIAL_DELAY,
    backoff: float = RetryConfig.BACKOFF_FACTOR,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int], None] | None = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """重试装饰器
    
    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟（秒）
        backoff: 退避因子
        exceptions: 需要重试的异常类型
        on_retry: 重试回调函数
        
    Returns:
        装饰器函数
        
    Example:
        >>> @retry(max_attempts=3, delay=1.0)
        ... def unstable_api_call():
        ...     pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(
                            f"函数 {func.__name__} 重试 {max_attempts} 次后仍失败: {e}"
                        )
                        raise
                    
                    if on_retry:
                        on_retry(e, attempt)
                    else:
                        logger.warning(
                            f"函数 {func.__name__} 第 {attempt} 次尝试失败，"
                            f"{current_delay:.1f}秒后重试: {e}"
                        )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            raise RuntimeError(f"{func.__name__} 重试逻辑异常")
        
        return wrapper
    return decorator


def retry_network(
    max_attempts: int = RetryConfig.TELEGRAM_RETRY,
    delay: float = RetryConfig.INITIAL_DELAY
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """网络请求重试装饰器
    
    专门用于网络请求，捕获常见网络异常
    """
    return retry(
        max_attempts=max_attempts,
        delay=delay,
        exceptions=(RequestException, ConnectionError, TimeoutError)
    )


def retry_playwright(
    max_attempts: int = 2,
    delay: float = 1.0
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Playwright 操作重试装饰器
    
    专门用于 Playwright 操作，捕获超时和常见错误
    """
    return retry(
        max_attempts=max_attempts,
        delay=delay,
        exceptions=(PlaywrightTimeout, PlaywrightError)
    )

