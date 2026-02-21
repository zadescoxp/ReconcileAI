# ReconcileAI Deployment Guide

This guide walks you through deploying the ReconcileAI infrastructure to AWS.

## Prerequisites

1. **AWS Account**: Active AWS account with appropriate permissions
2. **AWS CLI**: Installed and configured
   ```bash
   aws configure
   ```
3. **Node.js**: Version 18 or higher
4. **AWS CDK**: Installed globally
   ```bash
   npm install -g aws-cdk
   ```

## Initial Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Build TypeScript Code

```bash
npm run build
```

### 3. Bootstrap CDK (First Time Only)

Bootstrap CDK in your AWS account and region:

```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

Replace `ACCOUNT-ID` with your AWS account ID and `REGION` with your target region (e.g., us-east-1).

Example:
```bash
cdk bootstrap aws://123456789012/us-east-1
```

## Deployment

### 1. Review Infrastructure Changes

Preview what will be deployed:

```bash
cdk diff
```

### 2. Deploy the Stack

Deploy all infrastructure:

```bash
cdk deploy
```

You'll be prompted to approve IAM changes and security group modifications. Type `y` to proceed.

### 3. Note the Outputs

After deployment, CDK will output important values:

```
Outputs:
ReconcileAI-dev.POsTableName = ReconcileAI-POs
ReconcileAI-dev.InvoicesTableName = ReconcileAI-Invoices
ReconcileAI-dev.AuditLogsTableName = ReconcileAI-AuditLogs
ReconcileAI-dev.InvoiceBucketName = reconcileai-invoices-123456789012
ReconcileAI-dev.UserPoolId = us-east-1_XXXXXXXXX
ReconcileAI-dev.UserPoolClientId = XXXXXXXXXXXXXXXXXXXXXXXXXX
ReconcileAI-dev.SESRuleSetName = ReconcileAI-RuleSet
```

Save these values - you'll need them for frontend configuration.

## Post-Deployment Configuration

### 1. Configure Amazon SES

Follow the instructions in [SES_SETUP.md](./SES_SETUP.md) to:
- Verify your email address or domain
- Activate the SES receipt rule set
- Test email reception

### 2. Create Initial Users

Create an admin user in Cognito:

```bash
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username admin@yourdomain.com \
  --user-attributes Name=email,Value=admin@yourdomain.com Name=email_verified,Value=true Name=name,Value="Admin User" \
  --temporary-password TempPassword123! \
  --message-action SUPPRESS
```

Add the user to the Admin group:

```bash
aws cognito-idp admin-add-user-to-group \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username admin@yourdomain.com \
  --group-name Admin
```

### 3. Set Custom Attribute

Set the role custom attribute:

```bash
aws cognito-idp admin-update-user-attributes \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username admin@yourdomain.com \
  --user-attributes Name=custom:role,Value=Admin
```

## Verification

### 1. Check DynamoDB Tables

```bash
aws dynamodb list-tables
```

You should see:
- ReconcileAI-POs
- ReconcileAI-Invoices
- ReconcileAI-AuditLogs

### 2. Check S3 Bucket

```bash
aws s3 ls | grep reconcileai
```

### 3. Check Cognito User Pool

```bash
aws cognito-idp list-user-pools --max-results 10
```

### 4. Check SES Configuration

```bash
aws ses describe-active-receipt-rule-set
```

## Updating the Stack

After making changes to infrastructure code:

```bash
npm run build
cdk diff  # Review changes
cdk deploy  # Apply changes
```

## Destroying the Stack

To remove all infrastructure (WARNING: This deletes all data):

```bash
cdk destroy
```

## Troubleshooting

### CDK Bootstrap Issues

If you see "CDK bootstrap stack not found":
```bash
cdk bootstrap --force
```

### Permission Errors

Ensure your AWS credentials have these permissions:
- CloudFormation (full access)
- IAM (create/update roles and policies)
- DynamoDB (create/update tables)
- S3 (create/update buckets)
- Cognito (create/update user pools)
- SES (create/update receipt rules)
- Lambda (create/update functions)

### Region Mismatch

Ensure you're deploying to the correct region:
```bash
export AWS_REGION=us-east-1
cdk deploy
```

Or specify in cdk.json context:
```json
{
  "context": {
    "reconcileai:region": "us-east-1"
  }
}
```

## AWS Free Tier Monitoring

Monitor your usage to stay within Free Tier limits:

1. **AWS Billing Dashboard**: Check daily usage
2. **CloudWatch Metrics**: Monitor Lambda invocations, DynamoDB requests
3. **S3 Storage**: Keep under 5GB
4. **Set up Billing Alarms**: Get notified if costs exceed $1

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name ReconcileAI-BillingAlarm \
  --alarm-description "Alert when estimated charges exceed $1" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 1.0 \
  --comparison-operator GreaterThanThreshold
```

## Next Steps

1. Deploy Lambda functions (Task 2-4)
2. Configure Step Functions workflow (Task 5)
3. Deploy React frontend (Task 7-9)
4. Run end-to-end tests (Task 6, 13)
