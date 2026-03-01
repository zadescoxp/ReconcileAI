# ReconcileAI Deployment Walkthrough

This guide provides step-by-step instructions for deploying and testing the complete ReconcileAI system.

## Prerequisites

Before starting, ensure you have:

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured (`aws configure`)
3. **Node.js** 18+ installed
4. **AWS CDK** installed globally (`npm install -g aws-cdk`)
5. **Python 3.11+** installed (for Lambda functions)
6. **jq** installed (for JSON parsing in scripts)

## Deployment Steps

### Step 1: Deploy Infrastructure

Run the full stack deployment script:

```bash
bash scripts/deploy-full-stack.sh
```

This script will:
- Install all dependencies
- Build TypeScript code
- Bootstrap CDK (if needed)
- Deploy all AWS infrastructure
- Configure frontend environment
- Build frontend application

**Expected Duration:** 10-15 minutes

**What Gets Deployed:**
- 3 DynamoDB tables (POs, Invoices, AuditLogs)
- 1 S3 bucket for PDF storage
- 1 Cognito User Pool with Admin/User groups
- 7 Lambda functions (PDF extraction, AI matching, fraud detection, etc.)
- 1 Step Functions state machine
- 1 API Gateway REST API
- 1 SNS topic for notifications
- SES receipt rule set (requires manual activation)

### Step 2: Verify Deployment

Verify all components are deployed correctly:

```bash
bash scripts/verify-deployment.sh
```

This will check:
- All DynamoDB tables exist
- S3 bucket is accessible
- Cognito User Pool is configured
- All Lambda functions are deployed
- Step Functions state machine is active
- API Gateway is accessible
- SNS topic is created

**Expected Output:** All checks should show ✓ (green checkmarks)

### Step 3: Configure Amazon SES

SES requires manual configuration for email receiving:

1. **Verify Email Address or Domain:**
   ```bash
   aws ses verify-email-identity --email-address invoices@yourdomain.com
   ```
   
   Check your email and click the verification link.

2. **Activate Receipt Rule Set:**
   ```bash
   aws ses set-active-receipt-rule-set --rule-set-name ReconcileAI-RuleSet
   ```

3. **Test Email Reception:**
   Send a test email with a PDF attachment to your verified address.

See `docs/SES_SETUP.md` for detailed instructions.

### Step 4: Create Admin User

Create an admin user for accessing the dashboard:

```bash
# Get User Pool ID from deployment outputs
USER_POOL_ID=$(jq -r '.["ReconcileAI-dev"].UserPoolId' cdk-outputs.json)

# Create admin user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username admin@yourdomain.com \
  --user-attributes Name=email,Value=admin@yourdomain.com Name=email_verified,Value=true Name=name,Value="Admin User" \
  --temporary-password TempPassword123! \
  --message-action SUPPRESS

# Add to Admin group
aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username admin@yourdomain.com \
  --group-name Admin

# Set custom role attribute
aws cognito-idp admin-update-user-attributes \
  --user-pool-id $USER_POOL_ID \
  --username admin@yourdomain.com \
  --user-attributes Name=custom:role,Value=Admin

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username admin@yourdomain.com \
  --password YourSecurePassword123! \
  --permanent
```

### Step 5: Subscribe to Notifications

Subscribe your email to receive admin notifications:

```bash
SNS_TOPIC_ARN=$(jq -r '.["ReconcileAI-dev"].AdminNotificationTopicArn' cdk-outputs.json)

aws sns subscribe \
  --topic-arn $SNS_TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-admin-email@domain.com
```

Check your email and confirm the subscription.

## Testing

### End-to-End Testing

Run the comprehensive E2E test suite:

```bash
bash scripts/test-e2e.sh
```

This tests:
1. **Authentication** - User creation and management
2. **PO Management** - Upload and retrieval
3. **Invoice Processing** - Complete workflow from PDF to approval
4. **Audit Trail** - Logging verification
5. **Free Tier Compliance** - Usage monitoring

**Expected Duration:** 1-2 minutes

### Create Demo Data

Generate sample POs and invoices for demonstration:

```bash
bash scripts/create-demo-data.sh
```

This creates:
- **3 Purchase Orders** with different scenarios
- **4 Demo Invoices** (if reportlab is installed):
  - Perfect match (auto-approval)
  - Price discrepancy (flagged for review)
  - Price spike (fraud detection)
  - Unknown vendor (fraud detection)

**Note:** Install reportlab for PDF generation:
```bash
pip3 install reportlab
```

### Test Frontend Locally

Start the React development server:

```bash
cd frontend
npm start
```

The dashboard will open at `http://localhost:3000`

**Test the following:**
1. Login with admin credentials
2. Upload a PO via the PO Management page
3. View invoices on the Dashboard
4. Approve/reject flagged invoices
5. View audit trail (Admin only)

## Demo Walkthrough

### Scenario 1: Perfect Match (Auto-Approval)

1. **Upload PO:**
   - Vendor: TechSupplies Inc
   - Items: 5 Laptops @ $1,200, 10 Mice @ $25
   - Total: $6,250

2. **Send Invoice Email:**
   - Matches PO exactly
   - System auto-approves within 60 seconds

3. **Verify:**
   - Check Step Functions execution (should be SUCCEEDED)
   - View invoice in dashboard (status: Approved)
   - Check audit logs for auto-approval entry

### Scenario 2: Price Discrepancy (Human Review)

1. **Upload PO:**
   - Vendor: Office Depot Pro
   - Items: 20 Chairs @ $150, 10 Desks @ $400
   - Total: $7,000

2. **Send Invoice Email:**
   - Chairs priced at $180 (20% higher)
   - Total: $7,600

3. **System Response:**
   - AI detects price discrepancy
   - Invoice flagged for review
   - Step Functions pauses

4. **Human Action:**
   - Approver reviews discrepancy
   - Views AI reasoning
   - Approves or rejects with comment

### Scenario 3: Fraud Detection

1. **Send Invoice from Unknown Vendor:**
   - Vendor: Suspicious Vendor LLC
   - No matching PO in system

2. **System Response:**
   - Fraud flag: UNRECOGNIZED_VENDOR
   - Invoice flagged for review
   - Admin notification sent

3. **Human Action:**
   - Admin investigates vendor
   - Rejects invoice or creates PO first

## Monitoring

### CloudWatch Logs

View Lambda execution logs:

```bash
# PDF Extraction logs
aws logs tail /aws/lambda/ReconcileAI-PDFExtraction --follow

# AI Matching logs
aws logs tail /aws/lambda/ReconcileAI-AIMatching --follow

# Fraud Detection logs
aws logs tail /aws/lambda/ReconcileAI-FraudDetection --follow
```

### Step Functions Executions

View workflow executions:

```bash
STATE_MACHINE_ARN=$(jq -r '.["ReconcileAI-dev"].StateMachineArn' cdk-outputs.json)

aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --max-results 10
```

### DynamoDB Data

Query invoices:

```bash
aws dynamodb scan \
  --table-name ReconcileAI-Invoices \
  --limit 10
```

Query audit logs:

```bash
aws dynamodb scan \
  --table-name ReconcileAI-AuditLogs \
  --limit 10
```

## AWS Free Tier Monitoring

### Set Up Billing Alarm

Create an alarm to notify when costs exceed $1:

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
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=Currency,Value=USD
```

### Monitor Usage

Check current usage:

```bash
# Lambda invocations (last 24h)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=ReconcileAI-PDFExtraction \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum

# S3 storage
aws s3 ls s3://$(jq -r '.["ReconcileAI-dev"].InvoiceBucketName' cdk-outputs.json) --recursive --summarize

# DynamoDB table size
aws dynamodb describe-table --table-name ReconcileAI-Invoices --query 'Table.TableSizeBytes'
```

### Free Tier Limits

| Service | Free Tier Limit | Current Usage |
|---------|----------------|---------------|
| Lambda Invocations | 1M/month | Check CloudWatch |
| Lambda Compute | 400,000 GB-seconds | Check CloudWatch |
| DynamoDB Storage | 25GB | Check table size |
| DynamoDB RCU | 25 units | On-Demand mode |
| DynamoDB WCU | 25 units | On-Demand mode |
| S3 Storage | 5GB | Check bucket size |
| S3 GET Requests | 20,000/month | Check CloudWatch |
| S3 PUT Requests | 2,000/month | Check CloudWatch |
| Step Functions | 4,000 transitions/month | Check executions |
| Cognito MAUs | 50,000 | Check user pool |
| SES Emails | 1,000/month | Check SES metrics |

## Troubleshooting

### Issue: CDK Deploy Fails

**Solution:**
```bash
# Re-bootstrap CDK
cdk bootstrap --force

# Clear CDK cache
rm -rf cdk.out

# Rebuild and deploy
npm run build
cdk deploy
```

### Issue: Lambda Function Timeout

**Solution:**
- Check CloudWatch logs for errors
- Increase timeout in `infrastructure/stacks/reconcile-ai-stack.ts`
- Redeploy: `cdk deploy`

### Issue: Step Functions Execution Fails

**Solution:**
```bash
# Get execution details
aws stepfunctions describe-execution --execution-arn <EXECUTION_ARN>

# Check Lambda logs for the failed step
aws logs tail /aws/lambda/<FUNCTION_NAME> --follow
```

### Issue: Frontend Can't Connect to API

**Solution:**
1. Verify API Gateway URL in `frontend/.env`
2. Check CORS configuration in API Gateway
3. Verify Cognito credentials are correct
4. Check browser console for errors

### Issue: SES Not Receiving Emails

**Solution:**
1. Verify email address: `aws ses list-verified-email-addresses`
2. Check receipt rule set is active: `aws ses describe-active-receipt-rule-set`
3. Verify S3 bucket permissions for SES
4. Check SES sandbox mode (may need to request production access)

## Cleanup

To remove all infrastructure and avoid charges:

```bash
# Delete all data from S3 bucket first
aws s3 rm s3://$(jq -r '.["ReconcileAI-dev"].InvoiceBucketName' cdk-outputs.json) --recursive

# Destroy CDK stack
cdk destroy

# Confirm deletion
```

**Warning:** This will permanently delete all data including POs, invoices, and audit logs.

## Next Steps

1. **Deploy to Production:**
   - Update `cdk.json` context for production environment
   - Configure custom domain for API Gateway
   - Set up AWS Amplify for frontend hosting
   - Enable CloudWatch alarms for monitoring

2. **Enhance Security:**
   - Implement API rate limiting
   - Add WAF rules to API Gateway
   - Enable MFA for Cognito users
   - Rotate credentials regularly

3. **Optimize Performance:**
   - Add CloudFront CDN for frontend
   - Implement DynamoDB caching with DAX
   - Optimize Lambda memory allocation
   - Add Lambda reserved concurrency

4. **Add Features:**
   - Email configuration UI
   - Advanced fraud detection patterns
   - Bulk PO upload
   - Invoice analytics dashboard
   - Export functionality for reports

## Support

For issues or questions:
- Check `docs/` directory for detailed documentation
- Review CloudWatch logs for errors
- Check AWS service quotas and limits
- Verify Free Tier usage in AWS Billing Dashboard

## Success Criteria

Your deployment is successful when:
- ✅ All infrastructure components are deployed
- ✅ Frontend loads and authentication works
- ✅ PO upload and search functions correctly
- ✅ Invoice processing workflow completes end-to-end
- ✅ AI matching provides explainable results
- ✅ Fraud detection flags suspicious invoices
- ✅ Human approval workflow functions
- ✅ Audit trail captures all actions
- ✅ System stays within AWS Free Tier limits

Congratulations! Your ReconcileAI system is now operational. 🎉
