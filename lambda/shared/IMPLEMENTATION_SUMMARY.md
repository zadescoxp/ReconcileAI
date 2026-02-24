# Error Handling & Resilience Implementation Summary

## Overview

Task 12 implements comprehensive error handling and resilience features for ReconcileAI, including retry logic, structured logging, and admin notifications.

## Completed Components

### 1. Retry Utilities (`retry_utils.py`)

**Purpose**: Provide automatic retry logic with exponential backoff for transient errors.

**Features**:
- Generic exponential backoff with jitter function
- DynamoDB throttling retry decorator (`@retry_on_throttle`)
- Bedrock API retry decorator (`@retry_on_bedrock_error`)
- Retryable operation context manager

**Key Functions**:
```python
# Generic retry with exponential backoff
exponential_backoff_with_jitter(operation, max_retries=5, base_delay=1.0, max_delay=30.0)

# DynamoDB throttling decorator
@retry_on_throttle(max_retries=5)
def my_dynamodb_operation(): ...

# Bedrock API retry decorator
@retry_on_bedrock_error(max_retries=3)
def call_bedrock(): ...
```

**Error Codes Handled**:
- DynamoDB: `ProvisionedThroughputExceededException`, `ThrottlingException`, `RequestLimitExceeded`
- Bedrock: `ThrottlingException`, `ServiceUnavailable`, `InternalServerException`, `ModelTimeoutException`

### 2. CloudWatch Logger (`cloudwatch_logger.py`)

**Purpose**: Provide structured JSON logging for CloudWatch with context enrichment.

**Features**:
- Structured JSON log format
- Automatic context enrichment (function name, request ID)
- PII sanitization (passwords, tokens, secrets)
- Operation lifecycle logging
- Retry and throttle event logging
- Error logging with stack traces

**Key Classes**:
```python
# Structured logger
logger = StructuredLogger('FunctionName', context)
logger.log_operation_start('operation', details)
logger.log_operation_success('operation', details)
logger.log_operation_failure('operation', error, details)
logger.log_retry_attempt('operation', attempt, max_attempts, delay)
logger.log_throttle_event('service', 'operation')
```

**Log Format**:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "ERROR",
  "function": "PDFExtractionLambda",
  "request_id": "abc-123",
  "message": "Operation failed: extract_pdf",
  "context": {"s3_key": "invoices/2024/01/invoice.pdf"},
  "error": {
    "type": "PermanentError",
    "message": "PDF has no extractable text",
    "traceback": "..."
  }
}
```

### 3. Notification Service (`notification_service.py`)

**Purpose**: Send SNS notifications to admins for critical errors.

**Features**:
- Generic notification sending with severity levels
- Predefined notification methods for common scenarios
- Automatic message formatting
- Context inclusion in notifications

**Key Methods**:
```python
service = get_notification_service()

# Generic notification
service.send_notification(subject, message, severity, context)

# Predefined notifications
service.notify_step_function_failure(execution_arn, error, invoice_id)
service.notify_ai_service_unavailable(duration_minutes, failed_attempts)
service.notify_dynamodb_access_failure(table_name, operation, error)
service.notify_pdf_extraction_failure(s3_key, error)
service.notify_high_risk_invoice(invoice_id, vendor_name, risk_score, fraud_flags)
```

**Severity Levels**:
- `CRITICAL`: Immediate action required (system failures)
- `ERROR`: Significant issues requiring attention
- `WARNING`: Potential issues to monitor
- `INFO`: Informational messages

### 4. Infrastructure Updates

**SNS Topic**:
- Topic Name: `ReconcileAI-AdminNotifications`
- Purpose: Admin email notifications
- Free Tier: 1,000 emails/month

**Lambda Environment Variables**:
All Lambda functions now include:
```typescript
environment: {
  // ... existing variables
  SNS_TOPIC_ARN: this.adminNotificationTopic.topicArn,
}
```

**Lambda Permissions**:
All Lambda functions granted:
```typescript
this.adminNotificationTopic.grantPublish(lambdaFunction);
```

**Updated Functions**:
- `ReconcileAI-PDFExtraction`
- `ReconcileAI-AIMatching`
- `ReconcileAI-FraudDetection`
- `ReconcileAI-ResolveStep`

## Integration Pattern

### Lambda Function Integration

```python
import sys
import os

# Add shared directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from retry_utils import retry_on_throttle, retry_on_bedrock_error
from cloudwatch_logger import StructuredLogger
from notification_service import get_notification_service

def lambda_handler(event, context):
    # Initialize utilities
    logger = StructuredLogger('MyLambda', context)
    notification_service = get_notification_service()
    
    try:
        logger.log_operation_start('process_event', {'event_type': event.get('type')})
        
        # Use retry decorators
        result = process_with_retries(event)
        
        logger.log_operation_success('process_event', {'result': result})
        return result
        
    except PermanentError as e:
        logger.log_operation_failure('process_event', e)
        notification_service.notify_pdf_extraction_failure(
            s3_key=event.get('s3_key'),
            error=str(e)
        )
        return {'status': 'FLAGGED', 'error': str(e)}
        
    except Exception as e:
        logger.log_operation_failure('process_event', e)
        notification_service.send_notification(
            subject='Unexpected Error',
            message=str(e),
            severity='CRITICAL',
            context={'event': event}
        )
        raise

@retry_on_throttle(max_retries=5)
def store_in_dynamodb(data):
    table.put_item(Item=data)

@retry_on_bedrock_error(max_retries=3)
def call_bedrock_api(prompt):
    return bedrock_runtime.invoke_model(...)
```

## Error Handling Strategy

### 1. Transient Errors
**Strategy**: Automatic retry with exponential backoff

**Examples**:
- DynamoDB throttling
- Bedrock API rate limiting
- Network timeouts
- Lambda service exceptions

**Implementation**:
- Use `@retry_on_throttle` for DynamoDB operations
- Use `@retry_on_bedrock_error` for Bedrock calls
- Step Functions retry configuration (3 attempts, 2x backoff)

### 2. Permanent Errors
**Strategy**: Log, flag for manual review, notify admins

**Examples**:
- Malformed PDFs
- Missing required fields
- Invalid data formats

**Implementation**:
- Catch `PermanentError` exceptions
- Log to CloudWatch with full context
- Send SNS notification to admins
- Return flagged status (don't raise to avoid retries)

### 3. Business Logic Errors
**Strategy**: Route to approval workflow

**Examples**:
- Invoice/PO discrepancies
- Fraud flags detected
- Unrecognized vendors

**Implementation**:
- Pause Step Function execution
- Create approval request
- Notify approvers via dashboard and email

## Monitoring & Observability

### CloudWatch Logs
All Lambda functions log structured JSON to:
- `/aws/lambda/ReconcileAI-PDFExtraction`
- `/aws/lambda/ReconcileAI-AIMatching`
- `/aws/lambda/ReconcileAI-FraudDetection`
- `/aws/lambda/ReconcileAI-ResolveStep`

### CloudWatch Metrics
Monitor:
- Lambda invocations and errors
- Lambda duration and throttles
- DynamoDB throttled requests
- Step Functions failed executions
- SNS messages published

### SNS Notifications
Admins receive email alerts for:
- Step Function failures
- AI service unavailability (>30 minutes)
- DynamoDB access failures
- PDF extraction failures
- High-risk invoices (optional)

## AWS Free Tier Compliance

All error handling features stay within Free Tier:

| Service | Free Tier Limit | Usage |
|---------|----------------|-------|
| SNS Email | 1,000/month | ~50-100/month (critical errors only) |
| CloudWatch Logs | 5GB ingestion/month | ~500MB/month (structured JSON) |
| CloudWatch Metrics | 10 custom metrics | 0 (using default metrics only) |
| Lambda Invocations | 1M/month | Retry logic minimizes unnecessary calls |

**Cost Optimization**:
- Notifications sent only for critical errors
- Retry logic prevents excessive Lambda invocations
- Structured logging uses efficient JSON format
- No custom CloudWatch metrics (using defaults)

## Testing

### Unit Tests
Create tests for shared utilities:
```bash
cd lambda/shared
python -m pytest test_retry_utils.py
python -m pytest test_cloudwatch_logger.py
python -m pytest test_notification_service.py
```

### Integration Tests
Test error handling in Lambda functions:
```bash
cd tests/integration
python -m pytest test_error_handling.py
```

### Manual Testing
1. Test SNS notifications:
   ```bash
   aws sns publish --topic-arn [ARN] --subject "Test" --message "Test message"
   ```

2. Test Lambda retry logic:
   - Temporarily reduce DynamoDB capacity to trigger throttling
   - Verify retries in CloudWatch Logs

3. Test error notifications:
   - Upload malformed PDF to trigger extraction failure
   - Verify admin receives notification

## Documentation

Created documentation:
1. `docs/ERROR_HANDLING.md` - Comprehensive error handling guide
2. `docs/SNS_NOTIFICATION_SETUP.md` - SNS setup and configuration
3. `lambda/shared/README.md` - Shared utilities usage guide
4. `lambda/shared/IMPLEMENTATION_SUMMARY.md` - This document

## Deployment

### Step 1: Deploy Infrastructure
```bash
cd infrastructure
npm install
cdk deploy
```

### Step 2: Subscribe Admin Emails
```bash
aws sns subscribe \
  --topic-arn [TOPIC_ARN] \
  --protocol email \
  --notification-endpoint admin@example.com
```

### Step 3: Confirm Subscriptions
Check email and click confirmation link.

### Step 4: Test Notifications
```bash
aws sns publish \
  --topic-arn [TOPIC_ARN] \
  --subject "Test" \
  --message "Test notification"
```

## Next Steps

1. **Deploy infrastructure** with SNS topic
2. **Subscribe admin emails** to notification topic
3. **Test error handling** with sample failures
4. **Monitor CloudWatch Logs** for structured logging
5. **Tune notification thresholds** based on operational experience

## Requirements Validation

This implementation satisfies:
- **Requirement 16.1**: Lambda retry logic with exponential backoff ✓
- **Requirement 16.3**: AI service retry logic ✓
- **Requirement 16.4**: DynamoDB throttling backoff ✓
- **Requirement 16.5**: Error logging to CloudWatch ✓
- **Requirement 16.6**: Admin notifications for critical errors ✓

## AWS Free Tier Compliance

All components stay within Free Tier limits:
- SNS: 1,000 emails/month (using ~50-100/month)
- CloudWatch Logs: 5GB/month (using ~500MB/month)
- No additional costs incurred

## Summary

Task 12 successfully implements:
✅ Exponential backoff retry logic for DynamoDB and Bedrock
✅ Structured CloudWatch logging with context enrichment
✅ SNS notification system for admin alerts
✅ Infrastructure updates with SNS topic and permissions
✅ Comprehensive documentation and setup guides
✅ AWS Free Tier compliance maintained
