# ReconcileAI Deployment Checklist

Use this checklist to ensure a successful deployment of the ReconcileAI system.

## Pre-Deployment Checklist

### Prerequisites
- [ ] AWS Account created and accessible
- [ ] AWS CLI installed (`aws --version`)
- [ ] AWS CLI configured (`aws configure`)
- [ ] Node.js 18+ installed (`node --version`)
- [ ] AWS CDK installed globally (`cdk --version`)
- [ ] Python 3.11+ installed (`python3 --version`)
- [ ] jq installed for JSON parsing (`jq --version`)
- [ ] Git repository cloned locally

### AWS Account Verification
- [ ] AWS credentials configured correctly
- [ ] Sufficient IAM permissions for deployment
- [ ] Default region set (recommend: us-east-1)
- [ ] AWS account ID noted

### Repository Setup
- [ ] All dependencies installed (`npm install`)
- [ ] TypeScript compiles successfully (`npm run build`)
- [ ] No syntax errors in code

## Deployment Checklist

### Step 1: Infrastructure Deployment
- [ ] Run: `bash scripts/deploy-full-stack.sh`
- [ ] CDK bootstrap completed successfully
- [ ] All CloudFormation stacks deployed
- [ ] No deployment errors in output
- [ ] `cdk-outputs.json` file created
- [ ] `deployment-info.txt` file created
- [ ] Note User Pool ID from outputs
- [ ] Note API Gateway URL from outputs
- [ ] Note S3 Bucket name from outputs
- [ ] Note SNS Topic ARN from outputs

**Expected Duration:** 10-15 minutes

### Step 2: Deployment Verification
- [ ] Run: `bash scripts/verify-deployment.sh`
- [ ] All DynamoDB tables verified (3 tables)
- [ ] S3 bucket accessible
- [ ] Cognito User Pool created
- [ ] Admin and User groups exist
- [ ] All Lambda functions deployed (7 functions)
- [ ] Step Functions state machine active
- [ ] API Gateway endpoints accessible
- [ ] SNS topic created
- [ ] Frontend environment configured
- [ ] `verification-report.txt` generated

**Expected Duration:** 1-2 minutes

### Step 3: Amazon SES Configuration
- [ ] Email address or domain chosen for receiving invoices
- [ ] Email verification initiated: `aws ses verify-email-identity --email-address your@email.com`
- [ ] Verification email received and link clicked
- [ ] Email verified: `aws ses list-verified-email-addresses`
- [ ] Receipt rule set activated: `aws ses set-active-receipt-rule-set --rule-set-name ReconcileAI-RuleSet`
- [ ] Active rule set confirmed: `aws ses describe-active-receipt-rule-set`
- [ ] Test email sent to verified address
- [ ] Test email received in S3 bucket

**Expected Duration:** 5-10 minutes (including email verification wait)

### Step 4: User Management
- [ ] Admin user created in Cognito
- [ ] Admin user added to Admin group
- [ ] Admin user custom:role attribute set to "Admin"
- [ ] Admin user password set to permanent
- [ ] Admin user credentials saved securely
- [ ] Test user created (optional)
- [ ] User login tested via frontend

**Commands:**
```bash
USER_POOL_ID=$(jq -r '.["ReconcileAI-dev"].UserPoolId' cdk-outputs.json)

# Create admin
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username admin@yourdomain.com \
  --user-attributes Name=email,Value=admin@yourdomain.com Name=email_verified,Value=true \
  --temporary-password TempPassword123! \
  --message-action SUPPRESS

# Add to group
aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username admin@yourdomain.com \
  --group-name Admin

# Set role
aws cognito-idp admin-update-user-attributes \
  --user-pool-id $USER_POOL_ID \
  --username admin@yourdomain.com \
  --user-attributes Name=custom:role,Value=Admin

# Set password
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username admin@yourdomain.com \
  --password YourSecurePassword123! \
  --permanent
```

**Expected Duration:** 2-3 minutes

### Step 5: Notification Setup
- [ ] Admin email address chosen for notifications
- [ ] SNS subscription created: `aws sns subscribe --topic-arn <ARN> --protocol email --notification-endpoint your@email.com`
- [ ] Confirmation email received
- [ ] Subscription confirmed via email link
- [ ] Subscription status verified: `aws sns list-subscriptions-by-topic --topic-arn <ARN>`

**Expected Duration:** 2-3 minutes

## Testing Checklist

### Step 6: End-to-End Testing
- [ ] Run: `bash scripts/test-e2e.sh`
- [ ] Test user created successfully
- [ ] Test PO uploaded to DynamoDB
- [ ] Test PO verified in database
- [ ] Test invoice PDF created (if reportlab installed)
- [ ] Test invoice uploaded to S3
- [ ] Step Functions execution triggered
- [ ] Invoice processing completed
- [ ] Audit logs created
- [ ] Free Tier usage within limits

**Expected Duration:** 2-3 minutes

### Step 7: Demo Data Creation
- [ ] reportlab installed: `pip3 install reportlab` (optional)
- [ ] Run: `bash scripts/create-demo-data.sh`
- [ ] 3 sample POs created
- [ ] POs verified in DynamoDB
- [ ] 4 demo invoice PDFs created (if reportlab installed)
- [ ] Demo invoices uploaded to S3
- [ ] Wait 2-3 minutes for processing
- [ ] Check Step Functions executions
- [ ] Verify invoice statuses in DynamoDB

**Expected Duration:** 3-5 minutes

### Step 8: Frontend Testing
- [ ] Navigate to frontend directory: `cd frontend`
- [ ] Install dependencies: `npm install` (if not done)
- [ ] Start dev server: `npm start`
- [ ] Frontend loads at http://localhost:3000
- [ ] Login page displays
- [ ] Login with admin credentials successful
- [ ] Dashboard displays
- [ ] Navigation menu works
- [ ] PO upload page accessible
- [ ] PO search page accessible
- [ ] Invoice list page accessible
- [ ] Invoice detail page accessible
- [ ] Audit trail page accessible (Admin only)
- [ ] Logout works

**Expected Duration:** 5-10 minutes

## Functional Testing Checklist

### PO Management
- [ ] Upload new PO via frontend
- [ ] PO appears in database
- [ ] Search for PO by number
- [ ] Search for PO by vendor
- [ ] View PO details
- [ ] PO data displays correctly

### Invoice Processing
- [ ] Send invoice email to verified address (or upload PDF to S3)
- [ ] Wait 60 seconds for processing
- [ ] Check Step Functions execution status
- [ ] Verify invoice in database
- [ ] Check invoice status (Approved/Flagged)
- [ ] View invoice in frontend
- [ ] AI reasoning displayed
- [ ] Matched PO displayed

### Approval Workflow
- [ ] Create invoice with discrepancy
- [ ] Invoice flagged for review
- [ ] View flagged invoice in frontend
- [ ] Discrepancies highlighted
- [ ] Fraud flags displayed (if any)
- [ ] Approve invoice with comment
- [ ] Invoice status updated to Approved
- [ ] Reject invoice with reason
- [ ] Invoice status updated to Rejected

### Audit Trail
- [ ] Access audit trail page (Admin)
- [ ] Audit logs displayed
- [ ] Filter by action type
- [ ] Filter by date range
- [ ] Search by entity ID
- [ ] View log details
- [ ] AI reasoning included in logs

## Monitoring Checklist

### CloudWatch Logs
- [ ] PDF Extraction logs accessible
- [ ] AI Matching logs accessible
- [ ] Fraud Detection logs accessible
- [ ] Resolve Step logs accessible
- [ ] API Gateway logs accessible
- [ ] No critical errors in logs

### Step Functions
- [ ] State machine executions visible
- [ ] Successful executions show SUCCEEDED status
- [ ] Failed executions show error details
- [ ] Execution history available

### DynamoDB
- [ ] POs table contains data
- [ ] Invoices table contains data
- [ ] AuditLogs table contains data
- [ ] GSIs working correctly

## AWS Free Tier Compliance Checklist

### Usage Monitoring
- [ ] Lambda invocations < 33,000/day (1M/month)
- [ ] S3 storage < 5GB
- [ ] DynamoDB storage < 25GB
- [ ] Step Functions executions < 133/day (4K/month)
- [ ] Cognito MAUs < 50,000
- [ ] SES emails < 33/day (1K/month)

### Billing Alarm
- [ ] Billing alarm created
- [ ] Alarm threshold set to $1
- [ ] Alarm notification email configured
- [ ] Test alarm (optional)

**Command:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name ReconcileAI-BillingAlarm \
  --alarm-description "Alert when charges exceed $1" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 1.0 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=Currency,Value=USD
```

## Documentation Checklist

### Files to Review
- [ ] `README.md` - Project overview
- [ ] `DEPLOYMENT_WALKTHROUGH.md` - Detailed deployment guide
- [ ] `FINAL_DEPLOYMENT_SUMMARY.md` - Summary of deliverables
- [ ] `docs/DEPLOYMENT.md` - Infrastructure deployment
- [ ] `docs/SES_SETUP.md` - SES configuration
- [ ] `docs/SNS_NOTIFICATION_SETUP.md` - Notification setup
- [ ] `docs/ERROR_HANDLING.md` - Error handling patterns
- [ ] `docs/INFRASTRUCTURE.md` - Architecture details
- [ ] `docs/LAMBDA_FUNCTIONS.md` - Lambda documentation

### Generated Files
- [ ] `cdk-outputs.json` - Deployment outputs saved
- [ ] `deployment-info.txt` - Deployment summary saved
- [ ] `verification-report.txt` - Verification results saved
- [ ] `frontend/.env` - Frontend environment configured

## Demo Preparation Checklist

### Demo Scenarios
- [ ] **Scenario 1: Perfect Match**
  - [ ] PO uploaded for TechSupplies Inc
  - [ ] Matching invoice sent
  - [ ] Auto-approval demonstrated
  - [ ] Audit log reviewed

- [ ] **Scenario 2: Price Discrepancy**
  - [ ] PO uploaded for Office Depot Pro
  - [ ] Invoice with price difference sent
  - [ ] Flagged for review
  - [ ] Human approval demonstrated
  - [ ] AI reasoning reviewed

- [ ] **Scenario 3: Fraud Detection**
  - [ ] Historical PO for Acme Supplies
  - [ ] Invoice with price spike sent
  - [ ] Fraud flag triggered
  - [ ] Admin notification received
  - [ ] Investigation demonstrated

- [ ] **Scenario 4: Unknown Vendor**
  - [ ] Invoice from unrecognized vendor sent
  - [ ] Fraud flag triggered
  - [ ] Rejection demonstrated

### Demo Walkthrough
- [ ] Login to dashboard
- [ ] Show PO management
- [ ] Show invoice list
- [ ] Show invoice details with AI reasoning
- [ ] Show approval workflow
- [ ] Show audit trail
- [ ] Show Free Tier compliance

## Production Readiness Checklist

### Security
- [ ] All IAM roles follow least privilege
- [ ] S3 bucket encryption enabled
- [ ] DynamoDB encryption enabled
- [ ] API Gateway uses Cognito authorizer
- [ ] HTTPS enforced on all endpoints
- [ ] CORS configured correctly
- [ ] Input sanitization implemented

### Performance
- [ ] Lambda functions use ARM architecture
- [ ] Lambda memory optimized
- [ ] DynamoDB On-Demand mode configured
- [ ] S3 lifecycle rules configured
- [ ] API Gateway caching considered

### Reliability
- [ ] Lambda retry logic implemented
- [ ] Step Functions retry configured
- [ ] Error handling in all functions
- [ ] CloudWatch logging enabled
- [ ] SNS notifications configured

### Compliance
- [ ] Audit logging comprehensive
- [ ] 7-year retention configured
- [ ] All actions logged
- [ ] AI reasoning captured
- [ ] User actions tracked

## Post-Deployment Checklist

### Immediate Actions
- [ ] Save all credentials securely
- [ ] Document API Gateway URL
- [ ] Document Cognito User Pool ID
- [ ] Share access with team members
- [ ] Schedule regular monitoring

### Optional Enhancements
- [ ] Deploy frontend to AWS Amplify
- [ ] Configure custom domain
- [ ] Add CloudFront CDN
- [ ] Enable X-Ray tracing
- [ ] Add CloudWatch dashboards
- [ ] Implement advanced fraud patterns
- [ ] Add bulk PO upload
- [ ] Create analytics dashboard

## Troubleshooting Checklist

### If Deployment Fails
- [ ] Check AWS credentials
- [ ] Verify IAM permissions
- [ ] Check CDK bootstrap status
- [ ] Review CloudFormation events
- [ ] Check for resource conflicts
- [ ] Verify region configuration

### If Tests Fail
- [ ] Check CloudWatch logs
- [ ] Verify DynamoDB tables exist
- [ ] Check S3 bucket permissions
- [ ] Verify Lambda function code
- [ ] Check Step Functions definition
- [ ] Review API Gateway configuration

### If Frontend Doesn't Work
- [ ] Verify `.env` file exists
- [ ] Check API Gateway URL
- [ ] Verify Cognito configuration
- [ ] Check CORS settings
- [ ] Review browser console errors
- [ ] Test API endpoints directly

## Success Criteria

Your deployment is successful when ALL of the following are true:

- ✅ All infrastructure deployed without errors
- ✅ All verification checks pass
- ✅ SES receiving emails successfully
- ✅ Admin user can login to frontend
- ✅ PO upload and search working
- ✅ Invoice processing workflow completes
- ✅ AI matching provides explainable results
- ✅ Fraud detection flags suspicious invoices
- ✅ Human approval workflow functions
- ✅ Audit trail captures all actions
- ✅ System stays within AWS Free Tier limits
- ✅ All demo scenarios work as expected

## Final Sign-Off

- [ ] All checklist items completed
- [ ] System tested end-to-end
- [ ] Demo scenarios prepared
- [ ] Documentation reviewed
- [ ] Team trained on system usage
- [ ] Monitoring configured
- [ ] Ready for production use

**Deployment Date:** _______________
**Deployed By:** _______________
**Verified By:** _______________

---

**Congratulations! Your ReconcileAI system is now fully deployed and operational.** 🎉

For support, refer to:
- `DEPLOYMENT_WALKTHROUGH.md` for detailed instructions
- `FINAL_DEPLOYMENT_SUMMARY.md` for summary
- `docs/` directory for technical documentation
- CloudWatch Logs for debugging
