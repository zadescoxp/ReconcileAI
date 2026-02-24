# SNS Notification Setup Guide

This guide explains how to set up and configure the SNS notification system for ReconcileAI admin alerts.

## Overview

ReconcileAI uses Amazon SNS (Simple Notification Service) to send email notifications to administrators when critical errors occur. This ensures admins are immediately aware of issues requiring attention.

## SNS Topic Details

- **Topic Name**: `ReconcileAI-AdminNotifications`
- **Purpose**: Send critical error alerts to system administrators
- **Protocol**: Email
- **Free Tier**: 1,000 email notifications per month (sufficient for production use)

## Notification Triggers

Admins receive notifications for:

1. **Step Function Failures**: When invoice processing fails after all retries
2. **AI Service Unavailability**: When Bedrock is unavailable for extended periods
3. **DynamoDB Access Failures**: When database operations fail after retries
4. **PDF Extraction Failures**: When invoices cannot be processed
5. **High-Risk Invoices**: When fraud detection identifies high-risk transactions (optional)

## Setup Instructions

### Step 1: Deploy Infrastructure

Deploy the CDK stack which creates the SNS topic:

```bash
cd infrastructure
npm install
cdk deploy
```

After deployment, note the SNS Topic ARN from the CloudFormation outputs:
```
AdminNotificationTopicArn = arn:aws:sns:us-east-1:123456789012:ReconcileAI-AdminNotifications
```

### Step 2: Subscribe Admin Email Addresses

#### Option A: Using AWS CLI

Subscribe an admin email address:

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:REGION:ACCOUNT_ID:ReconcileAI-AdminNotifications \
  --protocol email \
  --notification-endpoint admin@example.com
```

Replace:
- `REGION`: Your AWS region (e.g., `us-east-1`)
- `ACCOUNT_ID`: Your AWS account ID
- `admin@example.com`: Admin email address

#### Option B: Using AWS Console

1. Open the AWS SNS Console
2. Navigate to **Topics**
3. Find and click on `ReconcileAI-AdminNotifications`
4. Click **Create subscription**
5. Select **Protocol**: Email
6. Enter **Endpoint**: admin email address
7. Click **Create subscription**

### Step 3: Confirm Email Subscription

1. Check the admin email inbox
2. Look for email from "AWS Notifications"
3. Click the confirmation link in the email
4. You should see "Subscription confirmed!" message

**Important**: Subscriptions are not active until confirmed!

### Step 4: Add Multiple Admins (Optional)

Repeat Step 2 and Step 3 for each admin who should receive notifications.

### Step 5: Test Notifications

Send a test notification to verify setup:

```bash
aws sns publish \
  --topic-arn arn:aws:sns:REGION:ACCOUNT_ID:ReconcileAI-AdminNotifications \
  --subject "[ReconcileAI TEST] System Test" \
  --message "This is a test notification. If you receive this, the notification system is working correctly."
```

Check admin email inbox for the test message.

## Managing Subscriptions

### List All Subscriptions

```bash
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:REGION:ACCOUNT_ID:ReconcileAI-AdminNotifications
```

### Unsubscribe an Email

```bash
aws sns unsubscribe \
  --subscription-arn arn:aws:sns:REGION:ACCOUNT_ID:ReconcileAI-AdminNotifications:SUBSCRIPTION_ID
```

Get the subscription ARN from the list-subscriptions command.

### View Subscription Status

In AWS Console:
1. Go to SNS → Topics → ReconcileAI-AdminNotifications
2. Click **Subscriptions** tab
3. Check **Status** column (should be "Confirmed")

## Notification Format

Notifications follow this format:

**Subject**: `[ReconcileAI SEVERITY] Brief Description`

**Body**:
```
Severity: CRITICAL
Timestamp: 2024-01-15T10:30:00Z

Message:
[Detailed error message]

Context:
{
  "invoice_id": "123",
  "error": "Lambda timeout",
  ...
}

---
This is an automated notification from ReconcileAI.
Please review the issue and take appropriate action.
```

## Severity Levels

- **CRITICAL**: Immediate action required (system failures, data loss risk)
- **ERROR**: Significant issues requiring attention (processing failures)
- **WARNING**: Potential issues to monitor (high-risk invoices)
- **INFO**: Informational messages (system status updates)

## Notification Examples

### Step Function Failure
```
Subject: [ReconcileAI CRITICAL] Step Function Execution Failed

Severity: CRITICAL
Timestamp: 2024-01-15T10:30:00Z

Message:
A Step Function execution has failed after all retry attempts.

Execution ARN: arn:aws:states:us-east-1:123456789012:execution:ReconcileAI-InvoiceProcessing:abc123
Error: Lambda.Timeout
Invoice ID: inv-2024-001

Context:
{
  "execution_arn": "arn:aws:states:...",
  "error": "Lambda.Timeout",
  "invoice_id": "inv-2024-001"
}
```

### AI Service Unavailable
```
Subject: [ReconcileAI CRITICAL] AI Service Prolonged Unavailability

Severity: CRITICAL
Timestamp: 2024-01-15T10:30:00Z

Message:
Amazon Bedrock has been unavailable for 30 minutes.

Failed attempts: 15
Invoice processing is currently blocked.

Context:
{
  "duration_minutes": 30,
  "failed_attempts": 15,
  "service": "Amazon Bedrock"
}
```

### High-Risk Invoice
```
Subject: [ReconcileAI WARNING] High-Risk Invoice Detected: Acme Corp

Severity: WARNING
Timestamp: 2024-01-15T10:30:00Z

Message:
A high-risk invoice has been detected and flagged for review.

Invoice ID: inv-2024-001
Vendor: Acme Corp
Risk Score: 85/100

Fraud Flags:
- Price spike detected for 'Widget A': $150.00 vs historical avg $100.00 (50.0% increase)
- Invoice total $5,500.00 exceeds PO total $5,000.00 by 10.0%

Please review this invoice in the dashboard.
```

## Troubleshooting

### Not Receiving Notifications

1. **Check subscription status**: Ensure status is "Confirmed"
   ```bash
   aws sns list-subscriptions-by-topic --topic-arn [TOPIC_ARN]
   ```

2. **Check email spam folder**: AWS notifications may be filtered

3. **Verify Lambda permissions**: Ensure Lambda functions have `sns:Publish` permission
   ```bash
   aws lambda get-policy --function-name ReconcileAI-PDFExtraction
   ```

4. **Check CloudWatch Logs**: Look for SNS publish errors
   ```bash
   aws logs tail /aws/lambda/ReconcileAI-PDFExtraction --follow
   ```

### Too Many Notifications

If receiving excessive notifications:

1. **Review error patterns**: Check CloudWatch Logs for recurring errors
2. **Adjust notification thresholds**: Modify Lambda code to reduce notification frequency
3. **Implement notification throttling**: Add rate limiting in notification service

### Email Delivery Issues

1. **Verify email address**: Ensure email is valid and accessible
2. **Check SNS delivery logs**: Enable SNS delivery status logging
3. **Contact AWS Support**: For persistent delivery issues

## Cost Monitoring

SNS is included in AWS Free Tier:
- **1,000 email notifications/month**: Free
- **Additional emails**: $2.00 per 100,000 notifications

Monitor usage:
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/SNS \
  --metric-name NumberOfMessagesPublished \
  --dimensions Name=TopicName,Value=ReconcileAI-AdminNotifications \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-31T23:59:59Z \
  --period 86400 \
  --statistics Sum
```

## Best Practices

1. **Subscribe multiple admins**: Ensure redundancy in case one admin is unavailable
2. **Use distribution lists**: Subscribe team email aliases for better coverage
3. **Test regularly**: Send test notifications monthly to verify system health
4. **Monitor notification volume**: Set up CloudWatch alarms for excessive notifications
5. **Document response procedures**: Create runbooks for each notification type
6. **Review and tune**: Adjust notification thresholds based on operational experience

## Security Considerations

1. **Email security**: Use corporate email addresses with proper security controls
2. **Sensitive data**: Notifications may contain invoice details - ensure email security
3. **Access control**: Limit SNS topic permissions to Lambda functions only
4. **Audit trail**: All notifications are logged in CloudWatch for compliance

## Integration with Lambda Functions

All Lambda functions are pre-configured with SNS integration:

```python
# Environment variable automatically set by CDK
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')

# Notification service automatically uses this ARN
from lambda.shared.notification_service import get_notification_service

service = get_notification_service()
service.send_notification(
    subject='Error occurred',
    message='Details...',
    severity='CRITICAL'
)
```

No additional configuration needed in Lambda code.

## Support

For issues with SNS notifications:
1. Check CloudWatch Logs for error messages
2. Review AWS SNS Console for subscription status
3. Consult AWS SNS documentation: https://docs.aws.amazon.com/sns/
4. Contact AWS Support for service-level issues

## Related Documentation

- [Error Handling & Resilience](ERROR_HANDLING.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Infrastructure Documentation](INFRASTRUCTURE.md)
