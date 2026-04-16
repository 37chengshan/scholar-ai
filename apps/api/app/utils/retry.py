"""重试工具

提供指数退避重试功能，用于服务间HTTP调用
"""

import asyncio
import random
import logging
from functools import wraps
from typing import Callable, TypeVar, Optional, Tuple, Any

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    exceptions: Tuple[type, ...] = (Exception,),
    retry_on_status: Optional[set] = None
):
    """指数退避重试装饰器

    Args:
        max_retries: 最大重试次数 (默认3次)
        base_delay: 初始延迟秒数 (默认1秒)
        max_delay: 最大延迟秒数 (默认10秒)
        exceptions: 触发重试的异常类型元组
        retry_on_status: 触发重试的HTTP状态码集合 (如 {500, 502, 503})

    Returns:
        装饰器函数

    Example:
        @with_retry(max_retries=3, retry_on_status={500, 502, 503})
        async def fetch_data(url: str) -> dict:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = await func(*args, **kwargs)

                    # 检查HTTP状态码
                    if retry_on_status is not None and hasattr(result, 'status_code'):
                        if result.status_code in retry_on_status:
                            raise Exception(f"HTTP {result.status_code}")

                    return result

                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) exceeded for {func.__name__}",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "error": str(e)
                            }
                        )
                        raise

                    # 计算指数退避延迟: min(1000 * 2^attempt, 10000) + random*1000 ms
                    delay_ms = min(1000 * (2 ** attempt), max_delay * 1000)
                    jitter_ms = random.random() * 1000
                    delay_seconds = (delay_ms + jitter_ms) / 1000

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}, "
                        f"retrying in {delay_seconds:.2f}s...",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "delay": delay_seconds,
                            "error": str(e)
                        }
                    )

                    await asyncio.sleep(delay_seconds)

            # Should never reach here, but just in case
            raise last_exception or Exception("Retry loop exited unexpectedly")

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)

                    # 检查HTTP状态码
                    if retry_on_status is not None and hasattr(result, 'status_code'):
                        if result.status_code in retry_on_status:
                            raise Exception(f"HTTP {result.status_code}")

                    return result

                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) exceeded for {func.__name__}",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "error": str(e)
                            }
                        )
                        raise

                    # 计算指数退避延迟
                    delay_ms = min(1000 * (2 ** attempt), max_delay * 1000)
                    jitter_ms = random.random() * 1000
                    delay_seconds = (delay_ms + jitter_ms) / 1000

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}, "
                        f"retrying in {delay_seconds:.2f}s...",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "delay": delay_seconds,
                            "error": str(e)
                        }
                    )

                    # 同步版本使用time.sleep
                    import time
                    time.sleep(delay_seconds)

            raise last_exception or Exception("Retry loop exited unexpectedly")

        # 根据函数是否是异步函数返回对应的wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


async def fetch_with_retry(
    url: str,
    client,
    method: str = "GET",
    max_retries: int = 3,
    timeout: float = 30.0,
    **kwargs
):
    """带重试的HTTP请求辅助函数

    Args:
        url: 请求URL
        client: HTTP客户端 (如httpx.AsyncClient)
        method: HTTP方法 (默认GET)
        max_retries: 最大重试次数
        timeout: 请求超时秒数
        **kwargs: 传递给客户端的其他参数

    Returns:
        HTTP响应

    Example:
        async with httpx.AsyncClient() as client:
            response = await fetch_with_retry(
                "http://api.example.com/data",
                client,
                method="POST",
                json={"key": "value"}
            )
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            response = await client.request(
                method=method,
                url=url,
                timeout=timeout,
                **kwargs
            )

            # 只重试5xx错误
            if response.status_code >= 500:
                raise Exception(f"Server error: HTTP {response.status_code}")

            return response

        except Exception as e:
            last_exception = e

            if attempt == max_retries:
                logger.error(
                    f"Max retries exceeded for {url}",
                    extra={"url": url, "method": method, "error": str(e)}
                )
                raise

            # 分级超时策略
            # 健康检查: 5s / 普通API: 30s / AI操作: 300s
            delay_ms = min(1000 * (2 ** attempt), 10000)
            jitter_ms = random.random() * 1000
            delay_seconds = (delay_ms + jitter_ms) / 1000

            logger.warning(
                f"Request failed (attempt {attempt + 1}/{max_retries + 1}), "
                f"retrying in {delay_seconds:.2f}s: {str(e)}",
                extra={
                    "url": url,
                    "method": method,
                    "attempt": attempt + 1,
                    "delay": delay_seconds
                }
            )

            await asyncio.sleep(delay_seconds)

    raise last_exception or Exception("Retry loop exited unexpectedly")
