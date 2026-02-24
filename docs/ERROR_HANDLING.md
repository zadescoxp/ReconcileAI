# Error Handling & Resilience

This document describes the error handling and notification system implemented in ReconcileAI.

## Overview

ReconcileAI implements comprehensive error handling with:
- Exponential backoff with jitter for transient errors
- Automatic retry logic for DynamoDB throttling and Bedrock API failures
- Structured CloudWatch logging for debugging
- SNS notifications for critical errors

## Retry Utilities

### Location
`lambda/shared/retry_utils.py`

### Features

#### 1. Exponential Backoff with Jitter
Generic retry function with configurable parameters:
```python
from lambda.shared.retry_utils import exponential_backoff_with_jitter

result = exponential_backoff_with_jitter(
    operation=lambda: my_operation(),
    max_retries=5,
    base_delay=1.0,
    max_delay=30.0,
    retryable_exceptions=(ClientError,)
)
```

#### 2. DynamoDB Throttling Decorator
Automatically retry DynamoDB operations on throttling:
```python
from lambda.shared.retry_utils import retry_on_throttle

@retry_on_throttle(max_retries=5)
def my_dynamodb_operation():
    table.put_item(Item={...})
```

Handles these error codes:
- `ProvisionedThroughputExceededException`
- `ThrottlingException`
- `RequestLimitExceeded`

#### 3. Bedrock API Retry Decorator
Automatically retry Bedrock API calls on transient errors:
```python
from lambda.shared.retry_utils import retry_on_bedrock_error

@retry_on_bedrock_error(max_retries=3)
def call_bedrock():
    return bedrock_runtime.invoke_model(...)
```

Handles these error codes:
- `ThrottlingException`
- `ServiceUnavailable`
- `InternalServerException`
- `ModelTimeoutException`

#### 4. Retryable Operation Context Manager
For custom retry logic:
```python
from lambda.shared.retry_utils import RetryableOperation

with RetryableOperation(max_retries=5) as retry:
    result = retry.execute(
        lambda: my_operation(),
        retryable_exceptions=(ClientError,)
    )
```

## CloudWatch Logging

### Location
`lambda/shared/cloudwatch_logger.py`

### Features

#### Structured Logger
Provides structured JSON logging with context enrichment:
```python
from lambda.shared.cloudwatch_logger import StructuredLogger

logger = StructuredLogger('PDFExtractionLambda', context)

# Log operations
logger.log_operation_start('extract_pdf', {'s3_key': key})
logger.log_operation_success('extract_pdf', {'invoice_id': invoice_id})
logger.log_operation_failure('extract_pdf', error, {'s3_key': key})

# Log retries
logger.log_retry_attempt('bedrock_call', attempt=2, max_attempts=3, delay=4.0)

# Log throttling
logger.log_throttle_event('DynamoDB', 'put_item')

# Log API calls
logger.log_api_call('Bedrock', 'invoke_model', duration_ms=1234, success=True)
```

#### Log Sanitization
Automatically redacts sensitive fields:
- password
- token
- secret
- authorization
- api_key

## Notification Service

### Location
`lambda/shared/notification_service.py`

### SNS Topic
- **Topic Name**: `ReconcileAI-AdminNotifications`
- **Purpose**: Send critical error notifications to admins
- **Subscription**: Admins must subscribe their email addresses via AWS Console or CLI

### Features

#### Generic Notifications
```python
from lambda.shared.notification_service import get_notification_service

service = get_notification_service()
service.send_notification(
    subject='Critical Error',
    message='Something went wrong',
    severity='CRITICAL',
    context={'invoice_id': '123'}
)
```

#### Predefined Notification Methods

**Step Function Failure**:
```python
service.notify_step_function_failure(
    execution_arn='arn:aws:states:...',
    error='Lambda timeout',
    invoice_id='123'
)
```

**AI Service Unavailable**:
```python
service.notify_ai_service_unavailable(
    duration_minutes=30,
    failed_attempts=10
)
```

**DynamoDB Access Failure**:
```python
service.notify_dynamodb_access_failure(
    table_name='ReconcileAI-Invoices',
    operation='put_item',
    error='Access denied'
)
```

**PDF Extraction Failure**:
```python
service.notify_pdf_extraction_failure(
    s3_key='invoices/2024/01/invoice.pdf',
    error='Malformed PDF'
)
```

**High-Risk Invoice**:
```python
service.notify_high_risk_invoice(
    invoice_id='123',
    vendor_name='Acme Corp',
    risk_score=85,
    fraud_flags=[...]
)
```

## Error Categories

### 1. Transient Errors (Retry with Exponential Backoff)
- Lambda timeout or memory errors
- DynamoDB throttling
- Bedrock API rate limiting
- Network connectivity issues

**Handling**: Automatic retry with exponential backoff (up to 3-5 attempts)

### 2. Permanent Errors (Flag for Manual Review)
- Malformed PDF that cannot be parsed
- Invoice with no extractable text
- AI response that cannot be parsed
- Missing required fields in extracted data

**Handling**: Log error, flag invoice for manual review, send notification

### 3. Business Logic Errors (Route to Approval Workflow)
- Discrepancies between invoice and PO
- Fraud flags detected
- Unrecognized vendor
- Amount exceedances

**Handling**: Pause Step Function, create approval request, notify approvers

## Step Functions Retry Configuration

All Lambda tasks in the Step Functions workflow have retry logic:

```json
{
  "Retry": [
    {
      "ErrorEquals": [
        "Lambda.ServiceException",
        "Lambda.TooManyRequestsException"
      ],
      "IntervalSeconds": 2,
      "MaxAttempts": 3,
      "BackoffRate": 2.0
    },
    {
      "ErrorEquals": ["States.TaskFailed"],
      "IntervalSeconds": 5,
      "MaxAttempts": 3,
      "BackoffRate": 2.0
    }
  ],
  "Catch": [
    {
      "ErrorEquals": ["States.ALL"],
      "Next": "FlagForManualReview"
    }
  ]
}
```

## Lambda Function Updates

All Lambda functions have been updated to include:
1. SNS topic ARN in environment variables
2. Permissions to publish to SNS topic
3. Error handling with retry logic
4. Structured CloudWatch logging
5. Critical error notifications

## Setup Instructions

### 1. Deploy Infrastructure
```bash
cd infrastructure
npm install
cdk deploy
```

### 2. Subscribe Admin Emails to SNS Topic
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:REGION:ACCOUNT:ReconcileAI-AdminNotifications \
  --protocol email \
  --notification-endpoint admin@example.com
```

### 3. Confirm Email Subscription
Check admin email inbox for confirmation link and click to confirm.

### 4. Test Notifications
```bash
aws sns publish \
  --topic-arn arn:aws:sns:REGION:ACCOUNT:ReconcileAI-AdminNotifications \
  --subject "Test Notification" \
  --message "This is a test notification from ReconcileAI"
```

## Monitoring

### CloudWatch Logs
All Lambda functions log to CloudWatch Logs with structured JSON format:
- `/aws/lambda/ReconcileAI-PDFExtraction`
- `/aws/lambda/ReconcileAI-AIMatching`
- `/aws/lambda/ReconcileAI-FraudDetection`
- `/aws/lambda/ReconcileAI-ResolveStep`

### CloudWatch Metrics
Monitor these metrics:
- Lambda invocations
- Lambda errors
- Lambda duration
- DynamoDB throttled requests
- Step Functions failed executions

### SNS Delivery Status
Monitor SNS topic metrics:
- Number of messages published
- Number of notifications delivered
- Number of notifications failed

## Best Practices

1. **Always use retry decorators** for DynamoDB and Bedrock operations
2. **Log all errors** with sufficient context for debugging
3. **Send notifications** only for critical errors to avoid alert fatigue
4. **Use structured logging** for easier log analysis
5. **Monitor CloudWatch metrics** to detect issues early
6. **Test error handling** with unit tests and integration tests

## AWS Free Tier Compliance

The error handling system stays within AWS Free Tier limits:
- **SNS**: 1,000 email notifications/month (free tier)
- **CloudWatch Logs**: 5GB ingestion/month (free tier)
- **CloudWatch Metrics**: 10 custom metrics (free tier)

Notifications are sent only for critical errors to stay within limits.
