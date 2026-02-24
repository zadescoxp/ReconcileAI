# Shared Lambda Utilities

This directory contains shared utilities used across all Lambda functions in ReconcileAI.

## Modules

### 1. retry_utils.py
Provides retry logic with exponential backoff for transient errors.

**Features**:
- Generic exponential backoff with jitter
- DynamoDB throttling retry decorator
- Bedrock API retry decorator
- Retryable operation context manager

**Usage**:
```python
from lambda.shared.retry_utils import retry_on_throttle, retry_on_bedrock_error

@retry_on_throttle(max_retries=5)
def store_in_dynamodb():
    table.put_item(Item={...})

@retry_on_bedrock_error(max_retries=3)
def call_bedrock_api():
    return bedrock_runtime.invoke_model(...)
```

### 2. cloudwatch_logger.py
Provides structured logging for CloudWatch with context enrichment.

**Features**:
- Structured JSON logging
- Context enrichment (function name, request ID)
- Automatic PII sanitization
- Operation lifecycle logging
- Retry and throttle event logging

**Usage**:
```python
from lambda.shared.cloudwatch_logger import StructuredLogger

logger = StructuredLogger('MyLambdaFunction', context)
logger.log_operation_start('process_invoice', {'invoice_id': '123'})
logger.log_operation_success('process_invoice', {'result': 'approved'})
```

### 3. notification_service.py
Provides SNS notification service for admin alerts.

**Features**:
- Generic notification sending
- Predefined notification methods for common scenarios
- Automatic message formatting
- Context inclusion

**Usage**:
```python
from lambda.shared.notification_service import get_notification_service

service = get_notification_service()
service.notify_step_function_failure(
    execution_arn='arn:aws:states:...',
    error='Lambda timeout',
    invoice_id='123'
)
```

## Integration Guide

### Step 1: Copy shared directory to Lambda package
When deploying Lambda functions, ensure the `shared` directory is included in the deployment package.

### Step 2: Import utilities in Lambda functions
```python
import sys
import os

# Add shared directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from retry_utils import retry_on_throttle
from cloudwatch_logger import StructuredLogger
from notification_service import get_notification_service
```

### Step 3: Use utilities in Lambda handler
```python
def lambda_handler(event, context):
    logger = StructuredLogger('MyLambda', context)
    notification_service = get_notification_service()
    
    try:
        logger.log_operation_start('process_event', {'event': event})
        
        # Your logic here with retry decorators
        result = process_with_retries()
        
        logger.log_operation_success('process_event', {'result': result})
        return result
        
    except Exception as e:
        logger.log_operation_failure('process_event', e)
        notification_service.send_notification(
            subject='Lambda Error',
            message=str(e),
            severity='CRITICAL'
        )
        raise
```

## Environment Variables

All Lambda functions using these utilities should have:
- `SNS_TOPIC_ARN`: ARN of the admin notification SNS topic

## Dependencies

These utilities require:
- `boto3` (included in Lambda runtime)
- `botocore` (included in Lambda runtime)

No additional dependencies needed.

## Testing

Unit tests for shared utilities are located in:
- `lambda/shared/test_retry_utils.py`
- `lambda/shared/test_cloudwatch_logger.py`
- `lambda/shared/test_notification_service.py`

Run tests:
```bash
cd lambda/shared
python -m pytest
```

## AWS Free Tier Compliance

These utilities are designed to stay within AWS Free Tier limits:
- Retry logic minimizes unnecessary Lambda invocations
- Structured logging uses efficient JSON format
- Notifications are sent only for critical errors
- No additional AWS services required
