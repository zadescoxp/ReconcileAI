"""
CloudWatch logging utilities for Lambda functions.
Provides structured logging with context for debugging and monitoring.
"""

import json
import logging
import traceback
from typing import Dict, Any, Optional
from datetime import datetime

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class StructuredLogger:
    """
    Structured logger for CloudWatch with context enrichment.
    """
    
    def __init__(self, function_name: str, context: Optional[Any] = None):
        """
        Initialize structured logger.
        
        Args:
            function_name: Name of the Lambda function
            context: Lambda context object
        """
        self.function_name = function_name
        self.request_id = context.request_id if context else 'unknown'
        self.aws_request_id = context.aws_request_id if context else 'unknown'
    
    def _log(
        self,
        level: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ):
        """Internal logging method with structured format."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'function': self.function_name,
            'request_id': self.request_id,
            'message': message
        }
        
        if extra:
            log_entry['context'] = extra
        
        if error:
            log_entry['error'] = {
                'type': type(error).__name__,
                'message': str(error),
                'traceback': traceback.format_exc()
            }
        
        log_message = json.dumps(log_entry)
        
        if level == 'INFO':
            logger.info(log_message)
        elif level == 'WARNING':
            logger.warning(log_message)
        elif level == 'ERROR':
            logger.error(log_message)
        elif level == 'CRITICAL':
            logger.critical(log_message)
        else:
            logger.debug(log_message)
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log info message."""
        self._log('INFO', message, extra)
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log warning message."""
        self._log('WARNING', message, extra)
    
    def error(
        self,
        message: str,
        error: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """Log error message with optional exception."""
        self._log('ERROR', message, extra, error)
    
    def critical(
        self,
        message: str,
        error: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """Log critical error message."""
        self._log('CRITICAL', message, extra, error)
    
    def log_operation_start(self, operation: str, details: Optional[Dict[str, Any]] = None):
        """Log the start of an operation."""
        self.info(f"Starting operation: {operation}", extra=details)
    
    def log_operation_success(self, operation: str, details: Optional[Dict[str, Any]] = None):
        """Log successful completion of an operation."""
        self.info(f"Operation completed successfully: {operation}", extra=details)
    
    def log_operation_failure(
        self,
        operation: str,
        error: Exception,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log operation failure with error details."""
        self.error(f"Operation failed: {operation}", error=error, extra=details)
    
    def log_retry_attempt(self, operation: str, attempt: int, max_attempts: int, delay: float):
        """Log retry attempt."""
        self.warning(
            f"Retrying operation: {operation}",
            extra={
                'attempt': attempt,
                'max_attempts': max_attempts,
                'delay_seconds': delay
            }
        )
    
    def log_throttle_event(self, service: str, operation: str):
        """Log throttling event."""
        self.warning(
            f"Throttled by {service}",
            extra={'operation': operation}
        )
    
    def log_api_call(
        self,
        service: str,
        operation: str,
        duration_ms: Optional[float] = None,
        success: bool = True
    ):
        """Log API call with timing information."""
        self.info(
            f"API call: {service}.{operation}",
            extra={
                'service': service,
                'operation': operation,
                'duration_ms': duration_ms,
                'success': success
            }
        )


def log_lambda_event(event: Dict[str, Any], context: Any, function_name: str):
    """
    Log Lambda invocation event (sanitized).
    
    Args:
        event: Lambda event
        context: Lambda context
        function_name: Name of the function
    """
    # Sanitize event (remove sensitive data)
    sanitized_event = sanitize_event(event)
    
    logger.info(json.dumps({
        'timestamp': datetime.utcnow().isoformat(),
        'level': 'INFO',
        'function': function_name,
        'request_id': context.request_id if context else 'unknown',
        'message': 'Lambda invocation',
        'event': sanitized_event
    }))


def sanitize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize event by removing sensitive fields.
    
    Args:
        event: Original event
        
    Returns:
        Sanitized event
    """
    sensitive_fields = ['password', 'token', 'secret', 'authorization', 'api_key']
    
    def sanitize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = {}
        for key, value in d.items():
            if any(field in key.lower() for field in sensitive_fields):
                sanitized[key] = '***REDACTED***'
            elif isinstance(value, dict):
                sanitized[key] = sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [sanitize_dict(item) if isinstance(item, dict) else item for item in value]
            else:
                sanitized[key] = value
        return sanitized
    
    return sanitize_dict(event)


def log_error_with_context(
    error: Exception,
    context: Dict[str, Any],
    function_name: str
):
    """
    Log error with full context for debugging.
    
    Args:
        error: Exception that occurred
        context: Additional context (invoice_id, po_id, etc.)
        function_name: Name of the function
    """
    logger.error(json.dumps({
        'timestamp': datetime.utcnow().isoformat(),
        'level': 'ERROR',
        'function': function_name,
        'message': 'Error occurred',
        'error': {
            'type': type(error).__name__,
            'message': str(error),
            'traceback': traceback.format_exc()
        },
        'context': context
    }))
