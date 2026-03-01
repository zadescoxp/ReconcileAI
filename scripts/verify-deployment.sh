#!/bin/bash

# ReconcileAI Deployment Verification Script
# Verifies that all infrastructure components are deployed and connected

set -e

echo "========================================="
echo "ReconcileAI Deployment Verification"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Load deployment info
if [ ! -f cdk-outputs.json ]; then
    echo -e "${RED}ERROR: cdk-outputs.json not found. Run deployment first.${NC}"
    exit 1
fi

STACK_NAME=$(jq -r 'keys[0]' cdk-outputs.json)
AWS_REGION=$(aws configure get region || echo "us-east-1")

echo "Verifying deployment in region: $AWS_REGION"
echo ""

# Function to check resource
check_resource() {
    local name=$1
    local command=$2
    
    echo -n "Checking $name... "
    if eval "$command" &> /dev/null; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

# Check DynamoDB Tables
echo "========================================="
echo "DynamoDB Tables"
echo "========================================="
check_resource "POs Table" "aws dynamodb describe-table --table-name ReconcileAI-POs --region $AWS_REGION"
check_resource "Invoices Table" "aws dynamodb describe-table --table-name ReconcileAI-Invoices --region $AWS_REGION"
check_resource "AuditLogs Table" "aws dynamodb describe-table --table-name ReconcileAI-AuditLogs --region $AWS_REGION"
echo ""

# Check S3 Bucket
echo "========================================="
echo "S3 Storage"
echo "========================================="
BUCKET_NAME=$(jq -r ".[\"$STACK_NAME\"].InvoiceBucketName" cdk-outputs.json)
check_resource "Invoice Bucket ($BUCKET_NAME)" "aws s3 ls s3://$BUCKET_NAME --region $AWS_REGION"
echo ""

# Check Cognito
echo "========================================="
echo "Cognito Authentication"
echo "========================================="
USER_POOL_ID=$(jq -r ".[\"$STACK_NAME\"].UserPoolId" cdk-outputs.json)
check_resource "User Pool ($USER_POOL_ID)" "aws cognito-idp describe-user-pool --user-pool-id $USER_POOL_ID --region $AWS_REGION"

# Check user groups
echo -n "Checking Admin Group... "
if aws cognito-idp get-group --user-pool-id $USER_POOL_ID --group-name Admin --region $AWS_REGION &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

echo -n "Checking User Group... "
if aws cognito-idp get-group --user-pool-id $USER_POOL_ID --group-name User --region $AWS_REGION &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi
echo ""

# Check Lambda Functions
echo "========================================="
echo "Lambda Functions"
echo "========================================="
check_resource "PDF Extraction Lambda" "aws lambda get-function --function-name ReconcileAI-PDFExtraction --region $AWS_REGION"
check_resource "AI Matching Lambda" "aws lambda get-function --function-name ReconcileAI-AIMatching --region $AWS_REGION"
check_resource "Fraud Detection Lambda" "aws lambda get-function --function-name ReconcileAI-FraudDetection --region $AWS_REGION"
check_resource "Resolve Step Lambda" "aws lambda get-function --function-name ReconcileAI-ResolveStep --region $AWS_REGION"
check_resource "PO Management Lambda" "aws lambda get-function --function-name ReconcileAI-POManagement --region $AWS_REGION"
check_resource "Invoice Management Lambda" "aws lambda get-function --function-name ReconcileAI-InvoiceManagement --region $AWS_REGION"
check_resource "S3 Trigger Lambda" "aws lambda get-function --function-name ReconcileAI-S3Trigger --region $AWS_REGION"
echo ""

# Check Step Functions
echo "========================================="
echo "Step Functions"
echo "========================================="
STATE_MACHINE_ARN=$(jq -r ".[\"$STACK_NAME\"].StateMachineArn" cdk-outputs.json)
check_resource "Invoice Processing State Machine" "aws stepfunctions describe-state-machine --state-machine-arn $STATE_MACHINE_ARN --region $AWS_REGION"
echo ""

# Check API Gateway
echo "========================================="
echo "API Gateway"
echo "========================================="
API_ID=$(jq -r ".[\"$STACK_NAME\"].APIGatewayId" cdk-outputs.json)
API_URL=$(jq -r ".[\"$STACK_NAME\"].APIGatewayURL" cdk-outputs.json)
check_resource "REST API ($API_ID)" "aws apigateway get-rest-api --rest-api-id $API_ID --region $AWS_REGION"

echo "API Endpoints:"
echo "  - POST $API_URL/pos"
echo "  - GET  $API_URL/pos"
echo "  - GET  $API_URL/invoices"
echo "  - POST $API_URL/invoices/{id}/approve"
echo "  - POST $API_URL/invoices/{id}/reject"
echo "  - GET  $API_URL/audit-logs"
echo ""

# Check SNS Topic
echo "========================================="
echo "SNS Notifications"
echo "========================================="
SNS_TOPIC_ARN=$(jq -r ".[\"$STACK_NAME\"].AdminNotificationTopicArn" cdk-outputs.json)
check_resource "Admin Notification Topic" "aws sns get-topic-attributes --topic-arn $SNS_TOPIC_ARN --region $AWS_REGION"

# Check subscriptions
echo -n "Checking SNS subscriptions... "
SUBSCRIPTION_COUNT=$(aws sns list-subscriptions-by-topic --topic-arn $SNS_TOPIC_ARN --region $AWS_REGION --query 'length(Subscriptions)' --output text)
if [ "$SUBSCRIPTION_COUNT" -gt 0 ]; then
    echo -e "${GREEN}$SUBSCRIPTION_COUNT subscription(s)${NC}"
else
    echo -e "${YELLOW}No subscriptions (configure manually)${NC}"
fi
echo ""

# Check SES
echo "========================================="
echo "Amazon SES"
echo "========================================="
echo -n "Checking SES receipt rule set... "
if aws ses describe-active-receipt-rule-set --region $AWS_REGION &> /dev/null; then
    RULE_SET_NAME=$(aws ses describe-active-receipt-rule-set --region $AWS_REGION --query 'Metadata.Name' --output text)
    echo -e "${GREEN}✓ Active: $RULE_SET_NAME${NC}"
else
    echo -e "${YELLOW}Not configured (see docs/SES_SETUP.md)${NC}"
fi

echo -n "Checking verified identities... "
VERIFIED_COUNT=$(aws ses list-verified-email-addresses --region $AWS_REGION --query 'length(VerifiedEmailAddresses)' --output text 2>/dev/null || echo "0")
if [ "$VERIFIED_COUNT" -gt 0 ]; then
    echo -e "${GREEN}$VERIFIED_COUNT verified${NC}"
else
    echo -e "${YELLOW}None verified (see docs/SES_SETUP.md)${NC}"
fi
echo ""

# Check Frontend
echo "========================================="
echo "Frontend"
echo "========================================="
if [ -f frontend/.env ]; then
    echo -e "${GREEN}✓ Frontend environment configured${NC}"
    if [ -d frontend/build ]; then
        echo -e "${GREEN}✓ Frontend built${NC}"
    else
        echo -e "${YELLOW}Frontend not built (run: cd frontend && npm run build)${NC}"
    fi
else
    echo -e "${RED}✗ Frontend environment not configured${NC}"
fi
echo ""

# AWS Free Tier Usage Check
echo "========================================="
echo "AWS Free Tier Usage Estimates"
echo "========================================="
echo "Note: These are estimates. Check AWS Billing Dashboard for accurate usage."
echo ""

# Lambda invocations (last 24 hours)
echo -n "Lambda invocations (last 24h): "
LAMBDA_INVOCATIONS=$(aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Invocations \
    --dimensions Name=FunctionName,Value=ReconcileAI-PDFExtraction \
    --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 86400 \
    --statistics Sum \
    --region $AWS_REGION \
    --query 'Datapoints[0].Sum' \
    --output text 2>/dev/null || echo "0")
echo "$LAMBDA_INVOCATIONS (Free Tier: 1M/month)"

# DynamoDB read/write capacity
echo "DynamoDB: On-Demand mode (Free Tier: 25 WCU, 25 RCU)"

# S3 storage
echo -n "S3 storage: "
S3_SIZE=$(aws s3 ls s3://$BUCKET_NAME --recursive --summarize --region $AWS_REGION 2>/dev/null | grep "Total Size" | awk '{print $3}')
if [ -n "$S3_SIZE" ]; then
    S3_SIZE_MB=$((S3_SIZE / 1024 / 1024))
    echo "${S3_SIZE_MB}MB (Free Tier: 5GB)"
else
    echo "0MB (Free Tier: 5GB)"
fi

# Step Functions executions
echo -n "Step Functions executions (last 24h): "
SF_EXECUTIONS=$(aws stepfunctions list-executions \
    --state-machine-arn $STATE_MACHINE_ARN \
    --max-results 1000 \
    --region $AWS_REGION \
    --query 'length(executions)' \
    --output text 2>/dev/null || echo "0")
echo "$SF_EXECUTIONS (Free Tier: 4,000/month)"

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Verification Complete${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Summary saved to: verification-report.txt"

# Save report
cat > verification-report.txt << EOF
ReconcileAI Deployment Verification Report
===========================================

Date: $(date)
Region: $AWS_REGION

Infrastructure Status:
- DynamoDB Tables: Deployed
- S3 Bucket: Deployed
- Cognito User Pool: Deployed
- Lambda Functions: Deployed (7 functions)
- Step Functions: Deployed
- API Gateway: Deployed
- SNS Topic: Deployed

API Gateway URL: $API_URL
User Pool ID: $USER_POOL_ID

AWS Free Tier Usage (Last 24h):
- Lambda Invocations: $LAMBDA_INVOCATIONS / 1,000,000 per month
- S3 Storage: ${S3_SIZE_MB:-0}MB / 5GB
- Step Functions: $SF_EXECUTIONS / 4,000 per month

Next Steps:
1. Configure SES email receiving (docs/SES_SETUP.md)
2. Create admin user in Cognito
3. Subscribe to SNS notifications
4. Test the system with sample data
EOF

echo "To test the deployment, run: bash scripts/test-e2e.sh"
echo ""
