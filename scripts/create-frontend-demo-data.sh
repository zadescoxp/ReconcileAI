#!/bin/bash

# Create Demo Data for ReconcileAI Frontend
# This script creates sample POs and invoices for testing the dashboard

set -e

echo "🚀 Creating Demo Data for ReconcileAI..."

# Get CDK outputs
if [ ! -f "cdk-outputs.json" ]; then
    echo "❌ Error: cdk-outputs.json not found. Please deploy the stack first."
    exit 1
fi

# Extract values from CDK outputs
USER_POOL_ID=$(jq -r '.["ReconcileAI-dev"].UserPoolId' cdk-outputs.json)
API_URL=$(jq -r '.["ReconcileAI-dev"].APIGatewayURL' cdk-outputs.json)
POS_TABLE=$(jq -r '.["ReconcileAI-dev"].POsTableName' cdk-outputs.json)
INVOICES_TABLE=$(jq -r '.["ReconcileAI-dev"].InvoicesTableName' cdk-outputs.json)

echo "📊 Configuration:"
echo "  API URL: $API_URL"
echo "  POs Table: $POS_TABLE"
echo "  Invoices Table: $INVOICES_TABLE"
echo ""

# Create sample POs directly in DynamoDB
echo "📄 Creating sample Purchase Orders..."

# PO 1: TechSupplies Inc
aws dynamodb put-item --table-name "$POS_TABLE" --item '{
  "POId": {"S": "po-001"},
  "VendorName": {"S": "TechSupplies Inc"},
  "PONumber": {"S": "PO-2024-001"},
  "TotalAmount": {"N": "6250.00"},
  "UploadDate": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
  "UploadedBy": {"S": "admin@reconcileai.com"},
  "Status": {"S": "Active"},
  "LineItems": {"L": [
    {"M": {
      "LineNumber": {"N": "1"},
      "ItemDescription": {"S": "Dell Laptop XPS 15"},
      "Quantity": {"N": "5"},
      "UnitPrice": {"N": "1250.00"},
      "TotalPrice": {"N": "6250.00"},
      "MatchedQuantity": {"N": "0"}
    }}
  ]}
}'

# PO 2: Office Depot Pro
aws dynamodb put-item --table-name "$POS_TABLE" --item '{
  "POId": {"S": "po-002"},
  "VendorName": {"S": "Office Depot Pro"},
  "PONumber": {"S": "PO-2024-002"},
  "TotalAmount": {"N": "7000.00"},
  "UploadDate": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
  "UploadedBy": {"S": "admin@reconcileai.com"},
  "Status": {"S": "Active"},
  "LineItems": {"L": [
    {"M": {
      "LineNumber": {"N": "1"},
      "ItemDescription": {"S": "Office Chairs Ergonomic"},
      "Quantity": {"N": "10"},
      "UnitPrice": {"N": "350.00"},
      "TotalPrice": {"N": "3500.00"},
      "MatchedQuantity": {"N": "0"}
    }},
    {"M": {
      "LineNumber": {"N": "2"},
      "ItemDescription": {"S": "Standing Desks Adjustable"},
      "Quantity": {"N": "5"},
      "UnitPrice": {"N": "700.00"},
      "TotalPrice": {"N": "3500.00"},
      "MatchedQuantity": {"N": "0"}
    }}
  ]}
}'

# PO 3: Acme Supplies
aws dynamodb put-item --table-name "$POS_TABLE" --item '{
  "POId": {"S": "po-003"},
  "VendorName": {"S": "Acme Supplies"},
  "PONumber": {"S": "PO-2024-003"},
  "TotalAmount": {"N": "2500.00"},
  "UploadDate": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
  "UploadedBy": {"S": "admin@reconcileai.com"},
  "Status": {"S": "Active"},
  "LineItems": {"L": [
    {"M": {
      "LineNumber": {"N": "1"},
      "ItemDescription": {"S": "Printer Paper A4 - 500 sheets"},
      "Quantity": {"N": "50"},
      "UnitPrice": {"N": "25.00"},
      "TotalPrice": {"N": "1250.00"},
      "MatchedQuantity": {"N": "0"}
    }},
    {"M": {
      "LineNumber": {"N": "2"},
      "ItemDescription": {"S": "Ink Cartridges HP Black"},
      "Quantity": {"N": "25"},
      "UnitPrice": {"N": "50.00"},
      "TotalPrice": {"N": "1250.00"},
      "MatchedQuantity": {"N": "0"}
    }}
  ]}
}'

echo "✅ Created 3 sample Purchase Orders"
echo ""

# Create sample invoices
echo "📋 Creating sample Invoices..."

# Invoice 1: Approved (perfect match)
aws dynamodb put-item --table-name "$INVOICES_TABLE" --item '{
  "InvoiceId": {"S": "inv-001"},
  "VendorName": {"S": "TechSupplies Inc"},
  "InvoiceNumber": {"S": "INV-TS-2024-001"},
  "InvoiceDate": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
  "TotalAmount": {"N": "6250.00"},
  "Status": {"S": "Approved"},
  "MatchedPOIds": {"L": [{"S": "po-001"}]},
  "ReceivedDate": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
  "S3Key": {"S": "invoices/2024/03/inv-001.pdf"},
  "Discrepancies": {"L": []},
  "FraudFlags": {"L": []},
  "AIReasoning": {"S": "Perfect match found. All line items match PO-2024-001 within acceptable tolerances. No discrepancies detected."},
  "LineItems": {"L": [
    {"M": {
      "LineNumber": {"N": "1"},
      "ItemDescription": {"S": "Dell Laptop XPS 15"},
      "Quantity": {"N": "5"},
      "UnitPrice": {"N": "1250.00"},
      "TotalPrice": {"N": "6250.00"}
    }}
  ]}
}'

# Invoice 2: Flagged (price discrepancy)
aws dynamodb put-item --table-name "$INVOICES_TABLE" --item '{
  "InvoiceId": {"S": "inv-002"},
  "VendorName": {"S": "Office Depot Pro"},
  "InvoiceNumber": {"S": "INV-OD-2024-002"},
  "InvoiceDate": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
  "TotalAmount": {"N": "8400.00"},
  "Status": {"S": "Flagged"},
  "MatchedPOIds": {"L": [{"S": "po-002"}]},
  "ReceivedDate": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
  "S3Key": {"S": "invoices/2024/03/inv-002.pdf"},
  "Discrepancies": {"L": [
    {"M": {
      "Type": {"S": "PRICE_MISMATCH"},
      "Description": {"S": "Office Chairs price increased from $350 to $420 (20% increase)"},
      "InvoiceLine": {"N": "1"},
      "POLine": {"N": "1"},
      "Difference": {"N": "700.00"}
    }}
  ]},
  "FraudFlags": {"L": [
    {"M": {
      "FlagType": {"S": "PRICE_SPIKE"},
      "Severity": {"S": "MEDIUM"},
      "Description": {"S": "Price spike detected: 20% above historical average"}
    }}
  ]},
  "AIReasoning": {"S": "Matched to PO-2024-002 but detected price discrepancy on line item 1. Office Chairs unit price increased from $350 to $420 (20% increase). Requires human approval."},
  "LineItems": {"L": [
    {"M": {
      "LineNumber": {"N": "1"},
      "ItemDescription": {"S": "Office Chairs Ergonomic"},
      "Quantity": {"N": "10"},
      "UnitPrice": {"N": "420.00"},
      "TotalPrice": {"N": "4200.00"}
    }},
    {"M": {
      "LineNumber": {"N": "2"},
      "ItemDescription": {"S": "Standing Desks Adjustable"},
      "Quantity": {"N": "6"},
      "UnitPrice": {"N": "700.00"},
      "TotalPrice": {"N": "4200.00"}
    }}
  ]}
}'

# Invoice 3: Processing
aws dynamodb put-item --table-name "$INVOICES_TABLE" --item '{
  "InvoiceId": {"S": "inv-003"},
  "VendorName": {"S": "Acme Supplies"},
  "InvoiceNumber": {"S": "INV-AS-2024-003"},
  "InvoiceDate": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
  "TotalAmount": {"N": "2500.00"},
  "Status": {"S": "Matching"},
  "MatchedPOIds": {"L": []},
  "ReceivedDate": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
  "S3Key": {"S": "invoices/2024/03/inv-003.pdf"},
  "Discrepancies": {"L": []},
  "FraudFlags": {"L": []},
  "AIReasoning": {"S": ""},
  "LineItems": {"L": [
    {"M": {
      "LineNumber": {"N": "1"},
      "ItemDescription": {"S": "Printer Paper A4 - 500 sheets"},
      "Quantity": {"N": "50"},
      "UnitPrice": {"N": "25.00"},
      "TotalPrice": {"N": "1250.00"}
    }},
    {"M": {
      "LineNumber": {"N": "2"},
      "ItemDescription": {"S": "Ink Cartridges HP Black"},
      "Quantity": {"N": "25"},
      "UnitPrice": {"N": "50.00"},
      "TotalPrice": {"N": "1250.00"}
    }}
  ]}
}'

# Invoice 4: Rejected
aws dynamodb put-item --table-name "$INVOICES_TABLE" --item '{
  "InvoiceId": {"S": "inv-004"},
  "VendorName": {"S": "Unknown Vendor LLC"},
  "InvoiceNumber": {"S": "INV-UV-2024-004"},
  "InvoiceDate": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
  "TotalAmount": {"N": "15000.00"},
  "Status": {"S": "Rejected"},
  "MatchedPOIds": {"L": []},
  "ReceivedDate": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"},
  "S3Key": {"S": "invoices/2024/03/inv-004.pdf"},
  "Discrepancies": {"L": []},
  "FraudFlags": {"L": [
    {"M": {
      "FlagType": {"S": "UNRECOGNIZED_VENDOR"},
      "Severity": {"S": "HIGH"},
      "Description": {"S": "No purchase orders found for this vendor"}
    }}
  ]},
  "AIReasoning": {"S": "No matching POs found for vendor Unknown Vendor LLC. Flagged as unrecognized vendor."},
  "LineItems": {"L": [
    {"M": {
      "LineNumber": {"N": "1"},
      "ItemDescription": {"S": "Suspicious Equipment"},
      "Quantity": {"N": "1"},
      "UnitPrice": {"N": "15000.00"},
      "TotalPrice": {"N": "15000.00"}
    }}
  ]}
}'

echo "✅ Created 4 sample Invoices (1 Approved, 1 Flagged, 1 Processing, 1 Rejected)"
echo ""

echo "✅ Demo data created successfully!"
echo ""
echo "📊 Summary:"
echo "  - 3 Purchase Orders"
echo "  - 4 Invoices (various statuses)"
echo ""
echo "🌐 You can now view the data in the dashboard:"
echo "  cd frontend && npm start"
echo "  Open http://localhost:3000"
echo ""
