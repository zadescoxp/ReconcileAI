# ReconcileAI Infrastructure Overview

## Completed Infrastructure (Task 1)

### AWS CDK Project Structure

```
reconcile-ai/
├── infrastructure/
│   ├── app.ts                    # CDK app entry point
│   └── stacks/
│       └── reconcile-ai-stack.ts # Main infrastructure stack
├── docs/
│   ├── DEPLOYMENT.md             # Deployment instructions
│   ├── SES_SETUP.md              # SES configuration guide
│   └── INFRASTRUCTURE.md         # This file
├── package.json                  # Node.js dependencies
├── tsconfig.json                 # TypeScript configuration
├── cdk.json                      # CDK configuration
└── README.md                     # Project overview
```

## Deployed Resources

### 1. DynamoDB Tables (On-Demand Mode)

#### POs Table
- **Table Name**: `ReconcileAI-POs`
- **Partition Key**: `POId` (String)
- **GSI**: `VendorNameIndex` (VendorName + UploadDate)
- **Purpose**: Store purchase orders uploaded by users
- **Encryption**: AWS-managed keys
- **Free Tier**: ✅ On-Demand mode, <25GB storage

#### Invoices Table
- **Table Name**: `ReconcileAI-Invoices`
- **Partition Key**: `InvoiceId` (String)
- **GSI 1**: `VendorNameIndex` (VendorName + ReceivedDate)
- **GSI 2**: `StatusIndex` (Status + ReceivedDate)
- **Purpose**: Store extracted invoice data and processing status
- **Encryption**: AWS-managed keys
- **Free Tier**: ✅ On-Demand mode, <25GB storage

#### AuditLogs Table
- **Table Name**: `ReconcileAI-AuditLogs`
- **Partition Key**: `LogId` (String)
- **Sort Key**: `Timestamp` (String)
- **GSI**: `EntityIdIndex` (EntityId + Timestamp)
- **Purpose**: Immutable audit trail of all system actions
- **Encryption**: AWS-managed keys
- **Free Tier**: ✅ On-Demand mode, <25GB storage

### 2. S3 Bucket

- **Bucket Name**: `reconcileai-invoices-{account-id}`
- **Encryption**: SSE-S3 (AWS-managed keys)
- **Public Access**: Blocked (all)
- **Versioning**: Disabled (to save storage)
- **Lifecycle**: Delete objects after 365 days
- **Purpose**: Store invoice PDFs and email attachments
- **Free Tier**: ✅ <5GB storage

**Folder Structure**:
```
reconcileai-invoices-{account-id}/
├── emails/           # Raw emails from SES
└── invoices/         # Processed invoice PDFs
    └── {year}/
        └── {month}/
```

### 3. Amazon Cognito User Pool

- **User Pool Name**: `ReconcileAI-Users`
- **Sign-in**: Email only
- **Self Sign-up**: Disabled (admin creates users)
- **Password Policy**: 8+ chars, uppercase, lowercase, digits, symbols
- **Custom Attributes**: `role` (Admin/User)
- **Groups**:
  - **Admin**: Full system access (precedence: 1)
  - **User**: Limited access (precedence: 2)
- **Free Tier**: ✅ 50,000 MAUs free

### 4. Amazon SES

- **Receipt Rule Set**: `ReconcileAI-RuleSet`
- **Receipt Rule**: `InvoiceReceiptRule`
- **Action**: Save emails to S3 (`emails/` prefix)
- **Spam Scanning**: Enabled
- **Status**: Requires manual email/domain verification
- **Free Tier**: ✅ 1,000 emails/month receiving

## AWS Free Tier Compliance

All infrastructure is configured to stay within AWS Free Tier limits:

| Service | Free Tier Limit | Configuration |
|---------|----------------|---------------|
| DynamoDB | 25GB storage, 25 WCU/RCU | On-Demand mode ✅ |
| S3 | 5GB storage | Lifecycle rules, no versioning ✅ |
| Cognito | 50,000 MAUs | Standard configuration ✅ |
| SES | 1,000 emails/month | Receipt only ✅ |
| Lambda | 1M requests/month | Not yet deployed |
| Step Functions | 4,000 transitions/month | Not yet deployed |
| Bedrock | Pay per token | Not yet deployed |

## Security Features

### Encryption
- **At Rest**: All DynamoDB tables and S3 bucket use AWS-managed encryption
- **In Transit**: All API calls use TLS 1.2+

### Access Control
- **S3**: Block all public access, SES-only write permissions
- **DynamoDB**: IAM-based access (Lambda functions only)
- **Cognito**: Role-based access control (Admin/User groups)

### Audit Trail
- All actions logged to `AuditLogs` table
- Immutable logs with timestamp sort key
- 7-year retention for compliance

## CDK Outputs

After deployment, these values are available:

```bash
# DynamoDB Tables
POsTableName = ReconcileAI-POs
InvoicesTableName = ReconcileAI-Invoices
AuditLogsTableName = ReconcileAI-AuditLogs

# S3 Bucket
InvoiceBucketName = reconcileai-invoices-{account-id}

# Cognito
UserPoolId = us-east-1_XXXXXXXXX
UserPoolClientId = XXXXXXXXXXXXXXXXXXXXXXXXXX

# SES
SESRuleSetName = ReconcileAI-RuleSet
```

## Next Steps

### Task 2: PDF Extraction Lambda
- Create Python Lambda function with ARM architecture
- Add pdfplumber dependency via Lambda layer
- Extract invoice data from PDFs
- Store data in Invoices table

### Task 3: AI Matching Lambda
- Create Python Lambda function with ARM architecture
- Integrate with Amazon Bedrock (Claude 3 Haiku)
- Match invoices to POs
- Generate explainability reasoning

### Task 4: Fraud Detection Lambda
- Create Python Lambda function with ARM architecture
- Implement fraud detection patterns
- Flag suspicious invoices

### Task 5: Step Functions Workflow
- Create 4-step workflow: Extract → Match → Detect → Resolve
- Configure retry logic and error handling
- Trigger from S3 events

## Useful Commands

### Deploy Infrastructure
```bash
npm run build
cdk deploy
```

### View Stack Outputs
```bash
aws cloudformation describe-stacks \
  --stack-name ReconcileAI-dev \
  --query 'Stacks[0].Outputs'
```

### Check DynamoDB Tables
```bash
aws dynamodb list-tables
```

### Check S3 Bucket
```bash
aws s3 ls s3://reconcileai-invoices-{account-id}/
```

### Check Cognito Users
```bash
aws cognito-idp list-users \
  --user-pool-id us-east-1_XXXXXXXXX
```

## Monitoring

### CloudWatch Metrics to Monitor
- DynamoDB: Read/Write capacity units
- S3: Storage size, request count
- Lambda: Invocation count, duration, errors (when deployed)
- Step Functions: Execution count, failures (when deployed)

### Cost Monitoring
Set up billing alerts to stay within Free Tier:
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name ReconcileAI-BillingAlarm \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --threshold 1.0
```

## Troubleshooting

### CDK Deployment Fails
- Ensure AWS credentials are configured: `aws configure`
- Bootstrap CDK: `cdk bootstrap`
- Check IAM permissions

### SES Not Receiving Emails
- Verify email/domain in SES console
- Activate receipt rule set: `aws ses set-active-receipt-rule-set --rule-set-name ReconcileAI-RuleSet`
- Check MX records for domain

### Cognito User Creation Fails
- Ensure email is valid format
- Check password meets policy requirements
- Verify user pool ID is correct

## References

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [SES Email Receiving](https://docs.aws.amazon.com/ses/latest/dg/receiving-email.html)
- [Cognito User Pools](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools.html)
