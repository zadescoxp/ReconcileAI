# Task 13: Final Integration & Testing - Deployment Guide

## Overview

This guide walks through the complete deployment and testing of ReconcileAI for Task 13 of the implementation plan. All scripts are already prepared and ready to execute.

## Prerequisites Checklist

Before starting deployment, ensure you have:

- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] AWS account with appropriate permissions
- [ ] Node.js (v18+) and npm installed
- [ ] AWS CDK CLI installed (`npm install -g aws-cdk`)
- [ ] Python 3.9+ installed (for Lambda functions)
- [ ] Git Bash or WSL (for running bash scripts on Windows)

## Task 13.1: Deploy Full Stack to AWS

### Step 1: Verify Prerequisites

```bash
# Check AWS CLI
aws --version

# Check AWS credentials
aws sts get-caller-identity

# Check Node.js
node --version

# Check CDK
cdk --version

# Check Python
python3 --version
```

### Step 2: Install Dependencies

```bash
# Install CDK dependencies
npm install

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### Step 3: Build TypeScript Code

```bash
# Compile TypeScript
npm run build
```

### Step 4: Run Full Stack Deployment

The deployment script will:
- Bootstrap CDK (if needed)
- Deploy all infrastructure (DynamoDB, S3, Lambda, Step Functions, API Gateway, Cognito, SNS)
- Configure frontend environment variables
- Build frontend

```bash
# Make script executable (if needed)
chmod +x scripts/deploy-full-stack.sh

# Run deployment
bash scripts/deploy-full-stack.sh
```

**Expected Duration:** 10-15 minutes

### Step 5: Post-Deployment Manual Configuration

After deployment completes, you'll need to:

#### A. Configure Amazon SES

```bash
# Verify your email address
aws ses verify-email-identity --email-address your-email@domain.com

# Check verification status
aws ses get-identity-verification-attributes --identities your-email@domain.com
```

See `docs/SES_SETUP.md` for detailed SES configuration.

#### B. Create Admin User

```bash
# Get User Pool ID from deployment outputs
USER_POOL_ID=$(jq -r '.[keys[0]].UserPoolId' cdk-outputs.json)

# Create admin user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username admin@yourdomain.com \
  --user-attributes Name=email,Value=admin@yourdomain.com Name=email_verified,Value=true \
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
```

#### C. Subscribe to SNS Notifications

```bash
# Get SNS Topic ARN from deployment outputs
SNS_TOPIC_ARN=$(jq -r '.[keys[0]].AdminNotificationTopicArn' cdk-outputs.json)

# Subscribe your email
aws sns subscribe \
  --topic-arn $SNS_TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-admin-email@domain.com

# Confirm subscription via email
```

### Step 6: Verify Deployment

```bash
# Run verification script
bash scripts/verify-deployment.sh
```

This will check:
- ✓ All DynamoDB tables created
- ✓ S3 bucket configured
- ✓ Cognito User Pool and groups
- ✓ All 7 Lambda functions deployed
- ✓ Step Functions state machine
- ✓ API Gateway endpoints
- ✓ SNS topic
- ✓ Frontend configuration

**Task 13.1 Complete** ✓

---

## Task 13.2: End-to-End Testing

### Step 1: Run Automated E2E Tests

```bash
# Run comprehensive end-to-end tests
bash scripts/test-e2e.sh
```

This script tests:
1. **Authentication**: User management and role-based access
2. **PO Management**: Upload and search functionality
3. **Invoice Processing**: Complete workflow from S3 → Step Functions → DynamoDB
4. **Audit Trail**: Logging completeness
5. **AWS Free Tier Compliance**: Usage verification

**Expected Duration:** 2-3 minutes

### Step 2: Manual Frontend Testing

```bash
# Start frontend locally
cd frontend
npm start
```

The app will open at `http://localhost:3000`

#### Test Cases:

**A. Login and Authentication**
- [ ] Login with admin user credentials
- [ ] Verify role-based navigation (Admin sees all features)
- [ ] Logout and login as regular user
- [ ] Verify User sees limited features

**B. PO Upload and Search**
- [ ] Navigate to PO Management
- [ ] Upload a sample PO (CSV or JSON format)
- [ ] Search for PO by number
- [ ] Search for PO by vendor name
- [ ] View PO details

**C. Invoice Review**
- [ ] Navigate to Invoices
- [ ] Filter by status (All, Flagged, Approved, Rejected)
- [ ] Click on an invoice to view details
- [ ] Verify matched PO is displayed
- [ ] Check discrepancies are highlighted
- [ ] Review AI reasoning section

**D. Approval Workflow**
- [ ] Find a flagged invoice
- [ ] Review discrepancies and fraud flags
- [ ] Add approval comment
- [ ] Approve invoice
- [ ] Verify status changes to "Approved"
- [ ] Test rejection workflow

**E. Audit Trail (Admin Only)**
- [ ] Navigate to Audit Trail
- [ ] Search by entity ID
- [ ] Filter by action type
- [ ] Verify all actions are logged
- [ ] Export audit logs to CSV

### Step 3: Test Email Ingestion (If SES Configured)

```bash
# Send test email with invoice PDF attachment to configured SES address
# Monitor Step Functions execution in AWS Console
```

### Step 4: Verify AWS Free Tier Usage

```bash
# Check current usage
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum

# Review verification report
cat verification-report.txt
```

**Verify:**
- [ ] Lambda invocations < 33,000/day (1M/month limit)
- [ ] S3 storage < 5GB
- [ ] Step Functions executions < 133/day (4,000/month limit)
- [ ] DynamoDB using On-Demand mode (within 25 WCU/RCU)

**Task 13.2 Complete** ✓

---

## Task 13.3: Create Demo Data and Walkthrough

### Step 1: Generate Demo Data

```bash
# Create sample POs and invoices
bash scripts/create-demo-data.sh
```

This creates:
- **3 Sample POs**: Perfect match, price discrepancy, historical data
- **4 Demo Invoices**: 
  - Invoice 1: Perfect match (auto-approves)
  - Invoice 2: Price discrepancy (flags for review)
  - Invoice 3: Price spike (fraud detection)
  - Invoice 4: Unknown vendor (fraud detection)

**Expected Duration:** 1-2 minutes

### Step 2: Wait for Processing

```bash
# Wait 2 minutes for Step Functions to process all invoices
sleep 120

# Check execution status
STATE_MACHINE_ARN=$(jq -r '.[keys[0]].StateMachineArn' cdk-outputs.json)
aws stepfunctions list-executions --state-machine-arn $STATE_MACHINE_ARN
```

### Step 3: Demo Walkthrough

#### Scenario 1: Perfect Match (Auto-Approval)

1. Open frontend dashboard
2. Navigate to Invoices
3. Find Invoice INV-2024-001 (TechSupplies Inc)
4. Verify status is "Approved"
5. View invoice details
6. Check AI reasoning: "Perfect match - all line items match within tolerance"
7. Navigate to Audit Trail
8. Search for this invoice ID
9. Verify auto-approval was logged with "System" as actor

**Expected Result:** ✓ Invoice auto-approved without human intervention

#### Scenario 2: Price Discrepancy (Human Approval)

1. Navigate to Invoices
2. Filter by "Flagged" status
3. Find Invoice INV-2024-002 (Office Depot Pro)
4. Click to view details
5. Observe discrepancies highlighted:
   - Office Chair: $180 vs $150 (20% higher)
6. Review AI reasoning explaining the discrepancy
7. Add comment: "Vendor confirmed price increase"
8. Click "Approve"
9. Verify status changes to "Approved"
10. Check Audit Trail for approval action

**Expected Result:** ✓ Discrepancy flagged, human reviewed and approved

#### Scenario 3: Fraud Detection - Price Spike

1. Navigate to Invoices
2. Find Invoice INV-2024-003 (Acme Supplies)
3. View details
4. Observe fraud flag: "PRICE_SPIKE"
5. Review evidence: "Paper Reams price $8.00 vs historical avg $5.00 (60% increase)"
6. Check AI reasoning
7. Demonstrate rejection workflow:
   - Add reason: "Price spike not justified"
   - Click "Reject"
8. Verify status changes to "Rejected"

**Expected Result:** ✓ Fraud detection triggered, invoice rejected

#### Scenario 4: Fraud Detection - Unrecognized Vendor

1. Navigate to Invoices
2. Find Invoice INV-2024-004 (Suspicious Vendor LLC)
3. View details
4. Observe fraud flag: "UNRECOGNIZED_VENDOR"
5. Review evidence: "No POs found for this vendor"
6. Check AI reasoning
7. Demonstrate escalation to admin

**Expected Result:** ✓ Unknown vendor flagged for review

### Step 4: Demonstrate Audit Trail

1. Navigate to Audit Trail (Admin only)
2. Show comprehensive logging:
   - PO uploads
   - Invoice receipts
   - PDF extractions
   - AI matching decisions
   - Fraud detections
   - Human approvals/rejections
3. Filter by action type: "InvoiceApproved"
4. Export audit logs to CSV
5. Open CSV and verify all required fields present

**Expected Result:** ✓ Complete audit trail for compliance

### Step 5: Demonstrate AWS Free Tier Compliance

1. Open AWS Console → Billing Dashboard
2. Show current month usage:
   - Lambda: Within 1M invocations
   - DynamoDB: On-Demand mode, within limits
   - S3: < 5GB storage
   - Step Functions: < 4,000 transitions
   - Bedrock: Minimal token usage (Claude 3 Haiku)
3. Show cost estimate: $0.00 (Free Tier)

**Expected Result:** ✓ All services within Free Tier limits

**Task 13.3 Complete** ✓

---

## Task 13 Completion Checklist

### Infrastructure Deployment
- [ ] CDK infrastructure deployed successfully
- [ ] All DynamoDB tables created
- [ ] S3 bucket configured
- [ ] Cognito User Pool with Admin/User groups
- [ ] All 7 Lambda functions deployed (ARM architecture)
- [ ] Step Functions state machine (4 steps)
- [ ] API Gateway with 6 endpoints
- [ ] SNS topic for notifications
- [ ] SES configured for email receiving

### Frontend Deployment
- [ ] Frontend environment variables configured
- [ ] Frontend built successfully
- [ ] Authentication working
- [ ] All pages accessible
- [ ] API integration working

### End-to-End Testing
- [ ] Authentication tested
- [ ] PO upload and search tested
- [ ] Invoice processing workflow tested
- [ ] Approval/rejection workflow tested
- [ ] Audit trail tested
- [ ] AWS Free Tier compliance verified

### Demo Data
- [ ] Sample POs created
- [ ] Demo invoices generated
- [ ] Perfect match scenario demonstrated
- [ ] Price discrepancy scenario demonstrated
- [ ] Fraud detection scenarios demonstrated
- [ ] Audit trail demonstrated

### Documentation
- [ ] Deployment information saved
- [ ] Verification report generated
- [ ] API endpoints documented
- [ ] Admin user credentials recorded
- [ ] Next steps documented

---

## Troubleshooting

### Issue: CDK Bootstrap Fails
**Solution:** Ensure AWS credentials have sufficient permissions. Run:
```bash
aws sts get-caller-identity
```

### Issue: Lambda Deployment Fails
**Solution:** Check Lambda function code exists in `lambda/` directories. Verify Python dependencies.

### Issue: Frontend Build Fails
**Solution:** 
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Issue: SES Email Not Received
**Solution:** 
1. Verify email address in SES
2. Check SES receipt rule set is active
3. Review SES receipt rules
4. Check S3 bucket permissions

### Issue: Step Functions Execution Fails
**Solution:**
1. Check CloudWatch Logs for Lambda errors
2. Verify IAM permissions for Lambda functions
3. Check DynamoDB table names match
4. Verify Bedrock access in region

### Issue: API Gateway 403 Errors
**Solution:**
1. Verify Cognito token is valid
2. Check API Gateway authorizer configuration
3. Verify CORS settings

---

## Next Steps After Task 13

1. **Production Hardening** (if deploying to production):
   - Enable DynamoDB point-in-time recovery
   - Configure CloudWatch alarms
   - Set up AWS Backup
   - Enable AWS WAF for API Gateway
   - Configure custom domain for frontend

2. **Monitoring Setup**:
   - Create CloudWatch dashboard
   - Set up billing alerts
   - Configure SNS notifications for errors

3. **Documentation**:
   - User guide for end users
   - Admin guide for system administrators
   - API documentation
   - Troubleshooting guide

4. **Competition Submission**:
   - Prepare demo video
   - Document architecture decisions
   - Highlight AWS Free Tier compliance
   - Showcase AI explainability features

---

## Success Criteria

Task 13 is complete when:

✓ All infrastructure deployed and verified
✓ Frontend accessible and functional
✓ End-to-end workflow tested successfully
✓ Demo data created and walkthrough completed
✓ AWS Free Tier compliance confirmed
✓ All audit logs present and complete
✓ Documentation generated

**Estimated Total Time:** 30-45 minutes (excluding SES email verification wait time)
