# ReconcileAI Backend Integration Tests

## Overview

This directory contains end-to-end integration tests that validate the complete ReconcileAI backend workflow:

1. **Email → S3 → Step Functions → DynamoDB**
2. **Perfect match invoice gets auto-approved**
3. **Flagged invoice pauses for approval**

## Prerequisites

### 1. AWS Infrastructure Deployed

Ensure the ReconcileAI stack is deployed to AWS:

```bash
cd infrastructure
npm install
cdk deploy
```

### 2. AWS Credentials Configured

Configure AWS credentials with permissions to access:
- DynamoDB tables (ReconcileAI-POs, ReconcileAI-Invoices, ReconcileAI-AuditLogs)
- S3 bucket (reconcileai-invoices-*)
- Step Functions state machine (ReconcileAI-InvoiceProcessing)

```bash
aws configure
```

### 3. Environment Variables

Set the following environment variables (get values from CDK outputs):

```bash
export INVOICE_BUCKET_NAME="reconcileai-invoices-123456789012"
export STATE_MACHINE_ARN="arn:aws:states:us-east-1:123456789012:stateMachine:ReconcileAI-InvoiceProcessing"
export POS_TABLE_NAME="ReconcileAI-POs"
export INVOICES_TABLE_NAME="ReconcileAI-Invoices"
export AUDIT_LOGS_TABLE_NAME="ReconcileAI-AuditLogs"
```

Or create a `.env` file:

```bash
INVOICE_BUCKET_NAME=reconcileai-invoices-123456789012
STATE_MACHINE_ARN=arn:aws:states:us-east-1:123456789012:stateMachine:ReconcileAI-InvoiceProcessing
POS_TABLE_NAME=ReconcileAI-POs
INVOICES_TABLE_NAME=ReconcileAI-Invoices
AUDIT_LOGS_TABLE_NAME=ReconcileAI-AuditLogs
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## Running the Tests

### Run All Integration Tests

```bash
pytest test_e2e_workflow.py -v -s
```

### Run Specific Test

```bash
# Test perfect match auto-approval
pytest test_e2e_workflow.py::test_perfect_match_auto_approval -v -s

# Test flagged invoice
pytest test_e2e_workflow.py::test_flagged_invoice_pauses_for_approval -v -s
```

### Run Tests Manually (without pytest)

```bash
python test_e2e_workflow.py
```

## Test Cases

### Test Case 1: Perfect Match Auto-Approval

**Scenario**: Invoice perfectly matches an existing PO

**Steps**:
1. Create test PO in DynamoDB (Acme Corp, $2,000)
2. Generate PDF invoice that matches PO exactly
3. Upload invoice to S3 (triggers Step Functions)
4. Wait for Step Functions execution to complete
5. Verify invoice status is "Approved"
6. Verify no discrepancies or fraud flags
7. Verify audit logs were created

**Expected Result**: Invoice is automatically approved without human intervention

### Test Case 2: Flagged Invoice Pauses for Approval

**Scenario**: Invoice from unrecognized vendor (no matching PO)

**Steps**:
1. Generate PDF invoice from "Suspicious Vendor" (no PO exists)
2. Upload invoice to S3 (triggers Step Functions)
3. Wait for Step Functions execution to complete
4. Verify invoice status is "Flagged"
5. Verify fraud flag "UNRECOGNIZED_VENDOR" exists
6. Verify invoice was NOT auto-approved
7. Verify audit logs were created

**Expected Result**: Invoice is flagged for human review and pauses workflow

## Troubleshooting

### Test Timeout

If tests timeout, check:
- Step Functions execution status in AWS Console
- Lambda function logs in CloudWatch
- DynamoDB table contents

### Permission Errors

Ensure your AWS credentials have the following permissions:
- `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:DeleteItem`, `dynamodb:Query`
- `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`
- `states:StartExecution`, `states:DescribeExecution`

### Lambda Errors

Check CloudWatch Logs for each Lambda function:
- `/aws/lambda/ReconcileAI-PDFExtraction`
- `/aws/lambda/ReconcileAI-AIMatching`
- `/aws/lambda/ReconcileAI-FraudDetection`
- `/aws/lambda/ReconcileAI-ResolveStep`

### Bedrock Access

Ensure Bedrock is enabled in your AWS region and you have access to Claude 3 Haiku model:

```bash
aws bedrock list-foundation-models --region us-east-1
```

## Cleanup

Tests automatically clean up test data after completion. If cleanup fails, manually delete:

1. Test POs from DynamoDB table `ReconcileAI-POs`
2. Test invoices from DynamoDB table `ReconcileAI-Invoices`
3. Test PDFs from S3 bucket `reconcileai-invoices-*`

## AWS Free Tier Considerations

These integration tests consume AWS resources:
- Lambda invocations (4 per test case)
- DynamoDB read/write operations (~10 per test case)
- S3 storage and requests (2 per test case)
- Step Functions state transitions (4 per test case)

**Recommendation**: Run integration tests sparingly (once per deployment) to stay within Free Tier limits.

## Next Steps

After successful integration tests:
1. Proceed to frontend development (Task 7)
2. Implement API Gateway endpoints (Task 10)
3. Deploy full stack to AWS (Task 13)
