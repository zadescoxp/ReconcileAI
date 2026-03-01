#!/bin/bash

# ReconcileAI Demo Data Creation Script
# Creates sample POs and invoices for demonstration

set -e

echo "========================================="
echo "ReconcileAI Demo Data Creation"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load deployment info
if [ ! -f cdk-outputs.json ]; then
    echo -e "${RED}ERROR: cdk-outputs.json not found. Deploy infrastructure first.${NC}"
    exit 1
fi

STACK_NAME=$(jq -r 'keys[0]' cdk-outputs.json)
BUCKET_NAME=$(jq -r ".[\"$STACK_NAME\"].InvoiceBucketName" cdk-outputs.json)
AWS_REGION=$(aws configure get region || echo "us-east-1")

echo "Creating demo data in region: $AWS_REGION"
echo ""

# Create demo directory
mkdir -p demo-data

# Sample PO 1: Perfect Match Scenario
echo "========================================="
echo "Creating Sample PO 1: Perfect Match"
echo "========================================="

PO1_ID="PO-DEMO-001-$(date +%s)"
cat > demo-data/po1.json << EOF
{
    "POId": {"S": "$PO1_ID"},
    "VendorName": {"S": "TechSupplies Inc"},
    "PONumber": {"S": "PO-2024-001"},
    "LineItems": {"L": [
        {"M": {
            "LineNumber": {"N": "1"},
            "ItemDescription": {"S": "Laptop Computer - Model X1"},
            "Quantity": {"N": "5"},
            "UnitPrice": {"N": "1200.00"},
            "TotalPrice": {"N": "6000.00"},
            "MatchedQuantity": {"N": "0"}
        }},
        {"M": {
            "LineNumber": {"N": "2"},
            "ItemDescription": {"S": "Wireless Mouse"},
            "Quantity": {"N": "10"},
            "UnitPrice": {"N": "25.00"},
            "TotalPrice": {"N": "250.00"},
            "MatchedQuantity": {"N": "0"}
        }}
    ]},
    "TotalAmount": {"N": "6250.00"},
    "UploadDate": {"S": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"},
    "UploadedBy": {"S": "demo-user"},
    "Status": {"S": "Active"}
}
EOF

aws dynamodb put-item \
    --table-name ReconcileAI-POs \
    --item file://demo-data/po1.json \
    --region $AWS_REGION

echo -e "${GREEN}✓ Created PO: $PO1_ID (TechSupplies Inc - \$6,250)${NC}"
echo ""

# Sample PO 2: Price Discrepancy Scenario
echo "========================================="
echo "Creating Sample PO 2: Price Discrepancy"
echo "========================================="

PO2_ID="PO-DEMO-002-$(date +%s)"
cat > demo-data/po2.json << EOF
{
    "POId": {"S": "$PO2_ID"},
    "VendorName": {"S": "Office Depot Pro"},
    "PONumber": {"S": "PO-2024-002"},
    "LineItems": {"L": [
        {"M": {
            "LineNumber": {"N": "1"},
            "ItemDescription": {"S": "Office Chair - Ergonomic"},
            "Quantity": {"N": "20"},
            "UnitPrice": {"N": "150.00"},
            "TotalPrice": {"N": "3000.00"},
            "MatchedQuantity": {"N": "0"}
        }},
        {"M": {
            "LineNumber": {"N": "2"},
            "ItemDescription": {"S": "Standing Desk"},
            "Quantity": {"N": "10"},
            "UnitPrice": {"N": "400.00"},
            "TotalPrice": {"N": "4000.00"},
            "MatchedQuantity": {"N": "0"}
        }}
    ]},
    "TotalAmount": {"N": "7000.00"},
    "UploadDate": {"S": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"},
    "UploadedBy": {"S": "demo-user"},
    "Status": {"S": "Active"}
}
EOF

aws dynamodb put-item \
    --table-name ReconcileAI-POs \
    --item file://demo-data/po2.json \
    --region $AWS_REGION

echo -e "${GREEN}✓ Created PO: $PO2_ID (Office Depot Pro - \$7,000)${NC}"
echo ""

# Sample PO 3: Historical data for fraud detection
echo "========================================="
echo "Creating Sample PO 3: Historical Data"
echo "========================================="

PO3_ID="PO-DEMO-003-$(date +%s)"
cat > demo-data/po3.json << EOF
{
    "POId": {"S": "$PO3_ID"},
    "VendorName": {"S": "Acme Supplies"},
    "PONumber": {"S": "PO-2024-003"},
    "LineItems": {"L": [
        {"M": {
            "LineNumber": {"N": "1"},
            "ItemDescription": {"S": "Paper Reams - A4"},
            "Quantity": {"N": "100"},
            "UnitPrice": {"N": "5.00"},
            "TotalPrice": {"N": "500.00"},
            "MatchedQuantity": {"N": "0"}
        }}
    ]},
    "TotalAmount": {"N": "500.00"},
    "UploadDate": {"S": "$(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ)"},
    "UploadedBy": {"S": "demo-user"},
    "Status": {"S": "Active"}
}
EOF

aws dynamodb put-item \
    --table-name ReconcileAI-POs \
    --item file://demo-data/po3.json \
    --region $AWS_REGION

echo -e "${GREEN}✓ Created PO: $PO3_ID (Acme Supplies - \$500)${NC}"
echo ""

# Create demo invoices (PDFs)
echo "========================================="
echo "Creating Demo Invoice PDFs"
echo "========================================="

# Check if reportlab is available
if python3 -c "import reportlab" 2>/dev/null; then
    echo "Creating invoice PDFs..."
    
    # Invoice 1: Perfect Match
    python3 << PYTHON_SCRIPT
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def create_invoice(filename, invoice_num, vendor, po_num, items, total):
    c = canvas.Canvas(filename, pagesize=letter)
    
    # Header
    c.setFont("Helvetica-Bold", 20)
    c.drawString(100, 750, "INVOICE")
    
    # Vendor info
    c.setFont("Helvetica", 12)
    c.drawString(100, 720, vendor)
    c.drawString(100, 705, "123 Business Street")
    c.drawString(100, 690, "Business City, BC 12345")
    c.drawString(100, 675, "Phone: (555) 123-4567")
    
    # Invoice details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(400, 720, f"Invoice #: {invoice_num}")
    c.setFont("Helvetica", 12)
    c.drawString(400, 705, f"Date: 2024-02-24")
    c.drawString(400, 690, f"PO #: {po_num}")
    c.drawString(400, 675, "Due: Net 30")
    
    # Line items header
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, 630, "Item Description")
    c.drawString(350, 630, "Qty")
    c.drawString(400, 630, "Unit Price")
    c.drawString(480, 630, "Total")
    
    c.line(100, 625, 550, 625)
    
    # Line items
    c.setFont("Helvetica", 11)
    y = 605
    for item in items:
        c.drawString(100, y, item['desc'][:40])
        c.drawString(350, y, str(item['qty']))
        c.drawString(400, y, f"\${item['price']:.2f}")
        c.drawString(480, y, f"\${item['total']:.2f}")
        y -= 20
    
    # Total
    c.line(100, y, 550, y)
    y -= 25
    c.setFont("Helvetica-Bold", 14)
    c.drawString(400, y, "TOTAL:")
    c.drawString(480, y, f"\${total:.2f}")
    
    # Footer
    c.setFont("Helvetica", 10)
    c.drawString(100, 100, "Payment Terms: Net 30 days")
    c.drawString(100, 85, "Thank you for your business!")
    
    c.save()
    print(f"Created: {filename}")

# Invoice 1: Perfect Match (will auto-approve)
create_invoice(
    "demo-data/invoice1-perfect-match.pdf",
    "INV-2024-001",
    "TechSupplies Inc",
    "PO-2024-001",
    [
        {"desc": "Laptop Computer - Model X1", "qty": 5, "price": 1200.00, "total": 6000.00},
        {"desc": "Wireless Mouse", "qty": 10, "price": 25.00, "total": 250.00}
    ],
    6250.00
)

# Invoice 2: Price Discrepancy (will flag for review)
create_invoice(
    "demo-data/invoice2-price-discrepancy.pdf",
    "INV-2024-002",
    "Office Depot Pro",
    "PO-2024-002",
    [
        {"desc": "Office Chair - Ergonomic", "qty": 20, "price": 180.00, "total": 3600.00},  # 20% higher
        {"desc": "Standing Desk", "qty": 10, "price": 400.00, "total": 4000.00}
    ],
    7600.00
)

# Invoice 3: Price Spike (fraud detection)
create_invoice(
    "demo-data/invoice3-price-spike.pdf",
    "INV-2024-003",
    "Acme Supplies",
    "PO-2024-004",
    [
        {"desc": "Paper Reams - A4", "qty": 100, "price": 8.00, "total": 800.00}  # 60% higher than historical
    ],
    800.00
)

# Invoice 4: Unrecognized Vendor (fraud detection)
create_invoice(
    "demo-data/invoice4-unknown-vendor.pdf",
    "INV-2024-004",
    "Suspicious Vendor LLC",
    "PO-2024-999",
    [
        {"desc": "Generic Office Supplies", "qty": 1, "price": 5000.00, "total": 5000.00}
    ],
    5000.00
)

print("All demo invoices created!")
PYTHON_SCRIPT

    echo -e "${GREEN}✓ Created 4 demo invoice PDFs${NC}"
    echo ""
    
    # Upload invoices to S3
    echo "Uploading demo invoices to S3..."
    for i in 1 2 3 4; do
        if [ -f "demo-data/invoice${i}-*.pdf" ]; then
            INVOICE_FILE=$(ls demo-data/invoice${i}-*.pdf)
            INVOICE_KEY="invoices/$(date +%Y)/$(date +%m)/demo-invoice-${i}-$(date +%s).pdf"
            aws s3 cp "$INVOICE_FILE" "s3://$BUCKET_NAME/$INVOICE_KEY" --region $AWS_REGION
            echo -e "${GREEN}✓ Uploaded: $(basename $INVOICE_FILE)${NC}"
            sleep 2  # Stagger uploads to avoid overwhelming the system
        fi
    done
    
else
    echo -e "${YELLOW}Warning: reportlab not installed. Skipping PDF creation.${NC}"
    echo "Install with: pip3 install reportlab"
fi

echo ""
echo "========================================="
echo "Demo Data Summary"
echo "========================================="
echo ""
echo "Purchase Orders Created:"
echo "  1. PO-2024-001 (TechSupplies Inc) - \$6,250 - Perfect match scenario"
echo "  2. PO-2024-002 (Office Depot Pro) - \$7,000 - Price discrepancy scenario"
echo "  3. PO-2024-003 (Acme Supplies) - \$500 - Historical data for fraud detection"
echo ""
echo "Demo Invoices:"
echo "  1. INV-2024-001 - Perfect match → Should auto-approve"
echo "  2. INV-2024-002 - Price discrepancy → Should flag for review"
echo "  3. INV-2024-003 - Price spike → Should trigger fraud detection"
echo "  4. INV-2024-004 - Unknown vendor → Should trigger fraud detection"
echo ""
echo -e "${BLUE}Demo data created successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Wait 1-2 minutes for invoices to process"
echo "2. Check Step Functions executions in AWS Console"
echo "3. View results in the frontend dashboard"
echo "4. Review audit logs for all actions"
echo ""
echo "To view processing status:"
echo "  aws stepfunctions list-executions --state-machine-arn \$(jq -r '.[\"$STACK_NAME\"].StateMachineArn' cdk-outputs.json) --region $AWS_REGION"
echo ""
