"""
Shared retry utilities for Lambda functions.
Provides exponential backoff with jitter for DynamoDB throttling and Bedrock API failures.
"""

import time
import random
from typing import Callable, Any, Optional
from functools import wraps
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def exponential_backoff_with_jitter(
    operation: Callable,
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: tuple = (Exception,)
) -> Any:
    """
    Execute operation with exponential backoff and jitter.
    
    Args:
        operation: Callable to execute
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (default 1.0)
        max_delay: Maximum delay in seconds (default 30.0)
        retryable_exceptions: Tuple of exception types to retry
        
    Returns:
        Result of operation
        
    Raises:
        Last exception if all retries exhausted
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return operation()
        except retryable_exceptions as e:
            last_exception = e
            
            if attempt == max_retries - 1:
                logger.error(f"All {max_retries} retry attempts exhausted")
                raise
            
            # Calculate delay with exponential backoff and jitter
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.1)  # Add up to 10% jitter
            total_delay = delay + jitter
            
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                f"Retrying in {total_delay:.2f}s..."
            )
            
            time.sleep(total_delay)
    
    # Should never reach here, but just in case
    if last_exception:
        raise last_exception


def retry_on_throttle(max_retries: int = 5):
    """
    Decorator for retrying DynamoDB operations on throttling.
    
    Usage:
        @retry_on_throttle(max_retries=5)
        def my_dynamodb_operation():
            table.put_item(Item={...})
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from botocore.exceptions import ClientError
            
            def operation():
                return func(*args, **kwargs)
            
            def is_throttle_error(e):
                if isinstance(e, ClientError):
                    error_code = e.response['Error']['Code']
                    return error_code in [
                        'ProvisionedThroughputExceededException',
                        'ThrottlingException',
                        'RequestLimitExceeded'
                    ]
                return False
            
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return operation()
                except ClientError as e:
                    if not is_throttle_error(e):
                        raise
                    
                    last_exception = e
                    
                    if attempt == max_retries - 1:
                        logger.error(f"DynamoDB throttling: all {max_retries} retries exhausted")
                        raise
                    
                    # Exponential backoff with jitter
                    delay = min(1.0 * (2 ** attempt), 30.0)
                    jitter = random.uniform(0, delay * 0.1)
                    total_delay = delay + jitter
                    
                    logger.warning(
                        f"DynamoDB throttled (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {total_delay:.2f}s..."
                    )
                    
                    time.sleep(total_delay)
            
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def retry_on_bedrock_error(max_retries: int = 3):
    """
    Decorator for retrying Bedrock API operations on transient errors.
    
    Usage:
        @retry_on_bedrock_error(max_retries=3)
        def call_bedrock():
            return bedrock_runtime.invoke_model(...)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from botocore.exceptions import ClientError
            
            def operation():
                return func(*args, **kwargs)
            
            def is_retryable_bedrock_error(e):
                if isinstance(e, ClientError):
                    error_code = e.response['Error']['Code']
                    return error_code in [
                        'ThrottlingException',
                        'ServiceUnavailable',
                        'InternalServerException',
                        'ModelTimeoutException'
                    ]
                return False
            
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return operation()
                except ClientError as e:
                    if not is_retryable_bedrock_error(e):
                        raise
                    
                    last_exception = e
                    
                    if attempt == max_retries - 1:
                        logger.error(f"Bedrock API error: all {max_retries} retries exhausted")
                        raise
                    
                    # Exponential backoff with jitter
                    delay = min(2.0 * (2 ** attempt), 60.0)
                    jitter = random.uniform(0, delay * 0.1)
                    total_delay = delay + jitter
                    
                    logger.warning(
                        f"Bedrock API error (attempt {attempt + 1}/{max_retries}): {error_code}. "
                        f"Retrying in {total_delay:.2f}s..."
                    )
                    
                    time.sleep(total_delay)
            
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


class RetryableOperation:
    """
    Context manager for retryable operations with custom retry logic.
    
    Usage:
        with RetryableOperation(max_retries=5) as retry:
            result = retry.execute(lambda: my_operation())
    """
    
    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 30.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
    
    def execute(
        self,
        operation: Callable,
        retryable_exceptions: tuple = (Exception,)
    ) -> Any:
        """Execute operation with retry logic."""
        return exponential_backoff_with_jitter(
            operation=operation,
            max_retries=self.max_retries,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            retryable_exceptions=retryable_exceptions
        )
