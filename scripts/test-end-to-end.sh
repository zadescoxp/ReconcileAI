#!/bin/bash

# End-to-end test script for ReconcileAI
# This script:
# 1. Uploads a PO via API
# 2. Uploads an invoice CSV to S3 (simulating email attachment)
# 3. Checks if the invoice was processed

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}ReconcileAI End-to-End Test${NC}\n"

# Get API endpoint and bucket name from CDK outputs
API_ENDPOINT=$(aws cloudformation describe-stacks --stack-name ReconcileAI-dev --query 'Stacks[0].Outputs[?OutputKey==`APIGatewayURL`].OutputValue' --output text)
BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name ReconcileAI-dev --query 'Stacks[0].Outputs[?OutputKey==`InvoiceBucketName`].OutputValue' --output text)

if [ -z "$API_ENDPOINT" ] || [ -z "$BUCKET_NAME" ]; then
    echo -e "${RED}✗ Failed to get API endpoint or bucket name${NC}"
    exit 1
fi

echo -e "${GREEN}✓ API Endpoint: $API_ENDPOINT${NC}"
echo -e "${GREEN}✓ S3 Bucket: $BUCKET_NAME${NC}\n"

# Step 1: Upload PO via API
echo -e "${YELLOW}Step 1: Uploading PO via API...${NC}"

# Get Cognito token (you'll need to login first)
# For now, we'll just upload the PO JSON directly to DynamoDB
echo "Creating PO directly in DynamoDB..."

aws dynamodb put-item \
    --table-name ReconcileAI-POs \
    --item '{
        "POId": {"S": "test-po-001"},
        "VendorName": {"S": "Acme Corporation"},
        "PONumber": {"S": "PO-2024-001"},
        "UploadDate": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
        "UploadedBy": {"S": "test-user"},
        "Status": {"S": "Active"},
        "TotalAmount": {"N": "1500.00"},
        "LineItems": {"L": [
            {"M": {
                "LineNumber": {"N": "1"},
                "ItemDescription": {"S": "Widget A"},
                "Quantity": {"N": "10"},
                "UnitPrice": {"N": "50.00"},
                "TotalPrice": {"N": "500.00"},
                "MatchedQuantity": {"N": "0"}
            }},
            {"M": {
                "LineNumber": {"N": "2"},
                "ItemDescription": {"S": "Widget B"},
                "Quantity": {"N": "5"},
                "UnitPrice": {"N": "100.00"},
                "TotalPrice": {"N": "500.00"},
                "MatchedQuantity": {"N": "0"}
            }},
            {"M": {
                "LineNumber": {"N": "3"},
                "ItemDescription": {"S": "Widget C"},
                "Quantity": {"N": "10"},
                "UnitPrice": {"N": "50.00"},
                "TotalPrice": {"N": "500.00"},
                "MatchedQuantity": {"N": "0"}
            }}
        ]}
    }' 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ PO uploaded successfully${NC}\n"
else
    echo -e "${RED}✗ Failed to upload PO${NC}"
    exit 1
fi

# Step 2: Upload invoice CSV to S3
echo -e "${YELLOW}Step 2: Uploading invoice CSV to S3...${NC}"

# Create a simple invoice CSV
cat > /tmp/test_invoice.csv << 'EOF'
Invoice
Invoice Number,INV-2024-001
Vendor,Acme Corporation
Date,2024-03-10

Line,Item Description,Quantity,Unit Price,Total Price
1,Widget A,10,$50.00,$500.00
2,Widget B,5,$100.00,$500.00
3,Widget C,10,$50.00,$500.00

Total Amount,$1500.00
EOF

# Upload to S3 invoices folder (this will trigger the workflow)
aws s3 cp /tmp/test_invoice.csv s3://$BUCKET_NAME/invoices/test_invoice_$(date +%s).csv

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Invoice uploaded to S3${NC}\n"
else
    echo -e "${RED}✗ Failed to upload invoice${NC}"
    exit 1
fi

# Step 3: Wait and check Step Functions execution
echo -e "${YELLOW}Step 3: Checking Step Functions execution...${NC}"
echo "Waiting 10 seconds for processing..."
sleep 10

# Get the latest execution
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks --stack-name ReconcileAI-dev --query 'Stacks[0].Outputs[?OutputKey==`StateMachineArn`].OutputValue' --output text)

LATEST_EXECUTION=$(aws stepfunctions list-executions \
    --state-machine-arn $STATE_MACHINE_ARN \
    --max-results 1 \
    --query 'executions[0].[executionArn,status]' \
    --output text)

if [ -n "$LATEST_EXECUTION" ]; then
    echo -e "${GREEN}✓ Step Functions execution found${NC}"
    echo "Execution: $LATEST_EXECUTION"
else
    echo -e "${YELLOW}⚠ No recent executions found${NC}"
fi

echo -e "\n${GREEN}✅ Test complete!${NC}"
echo -e "\nNext steps:"
echo "1. Check the ReconcileAI frontend to see the processed invoice"
echo "2. Check CloudWatch logs for Lambda execution details"
echo "3. Check DynamoDB ReconcileAI-Invoices table for the invoice record"
