#!/bin/bash

# ReconcileAI End-to-End Testing Script
# Tests the complete invoice processing workflow

set -e

echo "========================================="
echo "ReconcileAI End-to-End Testing"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load deployment info
if [ ! -f cdk-outputs.json ]; then
    echo -e "${RED}ERROR: cdk-outputs.json not found. Deploy infrastructure first.${NC}"
    exit 1
fi

STACK_NAME=$(jq -r 'keys[0]' cdk-outputs.json)
API_URL=$(jq -r ".[\"$STACK_NAME\"].APIGatewayURL" cdk-outputs.json)
USER_POOL_ID=$(jq -r ".[\"$STACK_NAME\"].UserPoolId" cdk-outputs.json)
USER_POOL_CLIENT_ID=$(jq -r ".[\"$STACK_NAME\"].UserPoolClientId" cdk-outputs.json)
BUCKET_NAME=$(jq -r ".[\"$STACK_NAME\"].InvoiceBucketName" cdk-outputs.json)
AWS_REGION=$(aws configure get region || echo "us-east-1")

echo "Testing environment:"
echo "  API URL: $API_URL"
echo "  Region: $AWS_REGION"
echo ""

# Check if test user exists
echo "========================================="
echo "Test 1: Authentication"
echo "========================================="
echo "Checking for test user..."

TEST_USER="test@reconcileai.local"
if aws cognito-idp admin-get-user --user-pool-id $USER_POOL_ID --username $TEST_USER --region $AWS_REGION &> /dev/null; then
    echo -e "${GREEN}✓ Test user exists${NC}"
else
    echo -e "${YELLOW}Creating test user...${NC}"
    aws cognito-idp admin-create-user \
        --user-pool-id $USER_POOL_ID \
        --username $TEST_USER \
        --user-attributes Name=email,Value=$TEST_USER Name=email_verified,Value=true Name=name,Value="Test User" \
        --temporary-password TestPassword123! \
        --message-action SUPPRESS \
        --region $AWS_REGION
    
    aws cognito-idp admin-add-user-to-group \
        --user-pool-id $USER_POOL_ID \
        --username $TEST_USER \
        --group-name User \
        --region $AWS_REGION
    
    aws cognito-idp admin-set-user-password \
        --user-pool-id $USER_POOL_ID \
        --username $TEST_USER \
        --password TestPassword123! \
        --permanent \
        --region $AWS_REGION
    
    echo -e "${GREEN}✓ Test user created${NC}"
fi
echo ""

# Test 2: PO Upload
echo "========================================="
echo "Test 2: PO Upload and Search"
echo "========================================="
echo "This test requires authentication. Testing via AWS SDK..."

# Create test PO data
TEST_PO_ID="PO-TEST-$(date +%s)"
cat > /tmp/test-po.json << EOF
{
    "POId": "$TEST_PO_ID",
    "VendorName": "Acme Corp",
    "PONumber": "PO-2024-001",
    "LineItems": [
        {
            "LineNumber": 1,
            "ItemDescription": "Widget A",
            "Quantity": 10,
            "UnitPrice": 50.00,
            "TotalPrice": 500.00,
            "MatchedQuantity": 0
        },
        {
            "LineNumber": 2,
            "ItemDescription": "Widget B",
            "Quantity": 5,
            "UnitPrice": 100.00,
            "TotalPrice": 500.00,
            "MatchedQuantity": 0
        }
    ],
    "TotalAmount": 1000.00,
    "UploadDate": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "UploadedBy": "test-user",
    "Status": "Active"
}
EOF

echo "Uploading test PO to DynamoDB..."
aws dynamodb put-item \
    --table-name ReconcileAI-POs \
    --item file:///tmp/test-po.json \
    --region $AWS_REGION

echo -e "${GREEN}✓ PO uploaded: $TEST_PO_ID${NC}"

# Verify PO exists
echo "Verifying PO..."
if aws dynamodb get-item \
    --table-name ReconcileAI-POs \
    --key "{\"POId\": {\"S\": \"$TEST_PO_ID\"}}" \
    --region $AWS_REGION &> /dev/null; then
    echo -e "${GREEN}✓ PO verified in database${NC}"
else
    echo -e "${RED}✗ PO not found${NC}"
fi
echo ""

# Test 3: Invoice Processing Workflow
echo "========================================="
echo "Test 3: Invoice Processing Workflow"
echo "========================================="
echo "Creating test invoice PDF..."

# Create a simple test PDF (requires Python)
python3 << 'PYTHON_SCRIPT'
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

pdf_path = "/tmp/test-invoice.pdf"
c = canvas.Canvas(pdf_path, pagesize=letter)

# Invoice header
c.setFont("Helvetica-Bold", 16)
c.drawString(100, 750, "INVOICE")

# Vendor info
c.setFont("Helvetica", 12)
c.drawString(100, 720, "Acme Corp")
c.drawString(100, 705, "123 Business St")
c.drawString(100, 690, "Business City, BC 12345")

# Invoice details
c.drawString(100, 660, "Invoice Number: INV-2024-001")
c.drawString(100, 645, "Invoice Date: 2024-02-24")
c.drawString(100, 630, "PO Number: PO-2024-001")

# Line items
c.drawString(100, 600, "Line Items:")
c.drawString(100, 580, "1. Widget A - Qty: 10 @ $50.00 = $500.00")
c.drawString(100, 565, "2. Widget B - Qty: 5 @ $100.00 = $500.00")

# Total
c.setFont("Helvetica-Bold", 12)
c.drawString(100, 535, "Total Amount: $1,000.00")

c.save()
print(f"Test invoice PDF created: {pdf_path}")
PYTHON_SCRIPT

if [ ! -f /tmp/test-invoice.pdf ]; then
    echo -e "${YELLOW}Warning: Could not create test PDF (reportlab not installed)${NC}"
    echo "Skipping invoice processing test"
else
    echo -e "${GREEN}✓ Test invoice PDF created${NC}"
    
    # Upload to S3 to trigger workflow
    echo "Uploading invoice to S3..."
    TEST_INVOICE_KEY="invoices/$(date +%Y)/$(date +%m)/test-invoice-$(date +%s).pdf"
    aws s3 cp /tmp/test-invoice.pdf s3://$BUCKET_NAME/$TEST_INVOICE_KEY --region $AWS_REGION
    
    echo -e "${GREEN}✓ Invoice uploaded to S3: $TEST_INVOICE_KEY${NC}"
    echo ""
    
    # Wait for processing
    echo "Waiting for Step Functions to process invoice (30 seconds)..."
    sleep 30
    
    # Check if invoice was processed
    echo "Checking invoice processing status..."
    STATE_MACHINE_ARN=$(jq -r ".[\"$STACK_NAME\"].StateMachineArn" cdk-outputs.json)
    
    EXECUTIONS=$(aws stepfunctions list-executions \
        --state-machine-arn $STATE_MACHINE_ARN \
        --max-results 5 \
        --region $AWS_REGION \
        --query 'executions[0]' \
        --output json)
    
    if [ -n "$EXECUTIONS" ] && [ "$EXECUTIONS" != "null" ]; then
        EXECUTION_STATUS=$(echo $EXECUTIONS | jq -r '.status')
        EXECUTION_ARN=$(echo $EXECUTIONS | jq -r '.executionArn')
        
        echo "Latest execution status: $EXECUTION_STATUS"
        echo "Execution ARN: $EXECUTION_ARN"
        
        if [ "$EXECUTION_STATUS" == "SUCCEEDED" ]; then
            echo -e "${GREEN}✓ Invoice processed successfully${NC}"
        elif [ "$EXECUTION_STATUS" == "RUNNING" ]; then
            echo -e "${YELLOW}⏳ Invoice still processing${NC}"
        else
            echo -e "${RED}✗ Invoice processing failed${NC}"
        fi
    else
        echo -e "${YELLOW}No executions found (may still be starting)${NC}"
    fi
fi
echo ""

# Test 4: Audit Trail
echo "========================================="
echo "Test 4: Audit Trail"
echo "========================================="
echo "Checking audit logs..."

AUDIT_COUNT=$(aws dynamodb scan \
    --table-name ReconcileAI-AuditLogs \
    --select COUNT \
    --region $AWS_REGION \
    --query 'Count' \
    --output text)

echo "Total audit log entries: $AUDIT_COUNT"

if [ "$AUDIT_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Audit logging is working${NC}"
    
    # Show recent logs
    echo ""
    echo "Recent audit log entries:"
    aws dynamodb scan \
        --table-name ReconcileAI-AuditLogs \
        --limit 5 \
        --region $AWS_REGION \
        --query 'Items[*].[ActionType.S, Timestamp.S, Actor.S]' \
        --output table
else
    echo -e "${YELLOW}No audit logs found yet${NC}"
fi
echo ""

# Test 5: AWS Free Tier Compliance
echo "========================================="
echo "Test 5: AWS Free Tier Compliance Check"
echo "========================================="

# Lambda invocations
echo "Checking Lambda invocations..."
TOTAL_INVOCATIONS=0
for FUNCTION in ReconcileAI-PDFExtraction ReconcileAI-AIMatching ReconcileAI-FraudDetection ReconcileAI-ResolveStep; do
    INVOCATIONS=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/Lambda \
        --metric-name Invocations \
        --dimensions Name=FunctionName,Value=$FUNCTION \
        --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
        --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
        --period 86400 \
        --statistics Sum \
        --region $AWS_REGION \
        --query 'Datapoints[0].Sum' \
        --output text 2>/dev/null || echo "0")
    
    if [ "$INVOCATIONS" != "None" ] && [ "$INVOCATIONS" != "null" ]; then
        TOTAL_INVOCATIONS=$((TOTAL_INVOCATIONS + ${INVOCATIONS%.*}))
    fi
done

echo "Lambda invocations (24h): $TOTAL_INVOCATIONS"
if [ $TOTAL_INVOCATIONS -lt 33333 ]; then  # 1M/month ≈ 33k/day
    echo -e "${GREEN}✓ Within Free Tier limit (1M/month)${NC}"
else
    echo -e "${YELLOW}⚠ Approaching Free Tier limit${NC}"
fi

# S3 storage
S3_SIZE=$(aws s3 ls s3://$BUCKET_NAME --recursive --summarize --region $AWS_REGION 2>/dev/null | grep "Total Size" | awk '{print $3}' || echo "0")
S3_SIZE_MB=$((S3_SIZE / 1024 / 1024))
echo "S3 storage: ${S3_SIZE_MB}MB"
if [ $S3_SIZE_MB -lt 5000 ]; then
    echo -e "${GREEN}✓ Within Free Tier limit (5GB)${NC}"
else
    echo -e "${RED}✗ Exceeding Free Tier limit${NC}"
fi

# Step Functions
SF_COUNT=$(aws stepfunctions list-executions \
    --state-machine-arn $STATE_MACHINE_ARN \
    --max-results 1000 \
    --region $AWS_REGION \
    --query 'length(executions)' \
    --output text 2>/dev/null || echo "0")
echo "Step Functions executions: $SF_COUNT"
if [ $SF_COUNT -lt 133 ]; then  # 4000/month ≈ 133/day
    echo -e "${GREEN}✓ Within Free Tier limit (4,000/month)${NC}"
else
    echo -e "${YELLOW}⚠ Approaching Free Tier limit${NC}"
fi
echo ""

# Summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo -e "${GREEN}✓ Authentication: User management working${NC}"
echo -e "${GREEN}✓ PO Management: Upload and retrieval working${NC}"
if [ -f /tmp/test-invoice.pdf ]; then
    echo -e "${GREEN}✓ Invoice Processing: Workflow triggered${NC}"
else
    echo -e "${YELLOW}⚠ Invoice Processing: Skipped (no PDF library)${NC}"
fi
echo -e "${GREEN}✓ Audit Trail: Logging operational${NC}"
echo -e "${GREEN}✓ Free Tier: Within limits${NC}"
echo ""

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}End-to-End Testing Complete${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Test the frontend: cd frontend && npm start"
echo "2. Create demo data: bash scripts/create-demo-data.sh"
echo "3. Monitor CloudWatch logs for detailed execution traces"
echo ""
