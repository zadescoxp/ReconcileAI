#!/usr/bin/env python3
"""
Create test audit logs in DynamoDB for ReconcileAI testing
"""
import boto3
from decimal import Decimal
from datetime import datetime, timedelta
import uuid

# Configuration
REGION = 'us-east-1'
AUDIT_LOGS_TABLE = 'ReconcileAI-AuditLogs'

def create_test_audit_logs():
    """Create test audit logs in DynamoDB"""
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table = dynamodb.Table(AUDIT_LOGS_TABLE)
    
    # Get the invoice IDs from our test invoices
    invoices_table = dynamodb.Table('ReconcileAI-Invoices')
    invoices_response = invoices_table.scan()
    invoices = invoices_response.get('Items', [])
    
    if len(invoices) < 3:
        print("Warning: Less than 3 invoices found. Creating audit logs anyway...")
    
    invoice_ids = [inv['InvoiceId'] for inv in invoices[:3]] if invoices else [
        str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    ]
    
    # Create audit logs for invoice processing workflow
    audit_logs = []
    
    # Invoice 1 - Complete workflow with approval
    if len(invoice_ids) > 0:
        base_time = datetime.now() - timedelta(hours=2)
        
        audit_logs.extend([
            {
                'LogId': str(uuid.uuid4()),
                'Timestamp': (base_time).isoformat() + 'Z',
                'Actor': 'system',
                'ActionType': 'InvoiceReceived',
                'EntityType': 'Invoice',
                'EntityId': invoice_ids[0],
                'Details': {
                    'invoiceNumber': 'INV-2024-001',
                    'vendorName': 'Acme Corp',
                    'totalAmount': '1250.00',
                    'source': 'email'
                }
            },
            {
                'LogId': str(uuid.uuid4()),
                'Timestamp': (base_time + timedelta(minutes=1)).isoformat() + 'Z',
                'Actor': 'system',
                'ActionType': 'InvoiceExtracted',
                'EntityType': 'Invoice',
                'EntityId': invoice_ids[0],
                'Details': {
                    'extractedFields': ['vendorName', 'invoiceNumber', 'totalAmount', 'lineItems'],
                    'confidence': Decimal('0.95')
                },
                'Reasoning': 'PDF extraction completed successfully using Textract. High confidence in extracted data.'
            },
            {
                'LogId': str(uuid.uuid4()),
                'Timestamp': (base_time + timedelta(minutes=2)).isoformat() + 'Z',
                'Actor': 'system',
                'ActionType': 'InvoiceMatched',
                'EntityType': 'Invoice',
                'EntityId': invoice_ids[0],
                'Details': {
                    'matchedPOId': 'po-001',
                    'matchScore': Decimal('0.85'),
                    'discrepancies': ['PRICE_MISMATCH']
                },
                'Reasoning': 'Matched to PO-001 with 85% confidence. Price discrepancy detected: Invoice price $125.00 exceeds PO price $100.00 by 25%.'
            },
            {
                'LogId': str(uuid.uuid4()),
                'Timestamp': (base_time + timedelta(minutes=3)).isoformat() + 'Z',
                'Actor': 'system',
                'ActionType': 'FraudDetected',
                'EntityType': 'Invoice',
                'EntityId': invoice_ids[0],
                'Details': {
                    'fraudFlags': [],
                    'riskScore': Decimal('0.2')
                },
                'Reasoning': 'No fraud indicators detected. Vendor is recognized and price variance is within acceptable range.'
            },
            {
                'LogId': str(uuid.uuid4()),
                'Timestamp': (base_time + timedelta(minutes=30)).isoformat() + 'Z',
                'Actor': '24d82498-2041-7063-6672-c513e92307 37',
                'ActionType': 'InvoiceApproved',
                'EntityType': 'Invoice',
                'EntityId': invoice_ids[0],
                'Details': {
                    'approverEmail': 'admin@reconcileai.com',
                    'comment': 'Approved after vendor confirmation',
                    'timestamp': (base_time + timedelta(minutes=30)).isoformat() + 'Z'
                }
            }
        ])
    
    # Invoice 2 - Auto-approved
    if len(invoice_ids) > 1:
        base_time = datetime.now() - timedelta(hours=1)
        
        audit_logs.extend([
            {
                'LogId': str(uuid.uuid4()),
                'Timestamp': (base_time).isoformat() + 'Z',
                'Actor': 'system',
                'ActionType': 'InvoiceReceived',
                'EntityType': 'Invoice',
                'EntityId': invoice_ids[1],
                'Details': {
                    'invoiceNumber': 'INV-2024-002',
                    'vendorName': 'Tech Supplies Inc',
                    'totalAmount': '500.00',
                    'source': 'email'
                }
            },
            {
                'LogId': str(uuid.uuid4()),
                'Timestamp': (base_time + timedelta(minutes=1)).isoformat() + 'Z',
                'Actor': 'system',
                'ActionType': 'InvoiceExtracted',
                'EntityType': 'Invoice',
                'EntityId': invoice_ids[1],
                'Details': {
                    'extractedFields': ['vendorName', 'invoiceNumber', 'totalAmount', 'lineItems'],
                    'confidence': Decimal('0.98')
                },
                'Reasoning': 'PDF extraction completed with high confidence. All required fields extracted successfully.'
            },
            {
                'LogId': str(uuid.uuid4()),
                'Timestamp': (base_time + timedelta(minutes=2)).isoformat() + 'Z',
                'Actor': 'system',
                'ActionType': 'InvoiceMatched',
                'EntityType': 'Invoice',
                'EntityId': invoice_ids[1],
                'Details': {
                    'matchedPOId': 'po-002',
                    'matchScore': Decimal('1.0'),
                    'discrepancies': []
                },
                'Reasoning': 'Perfect match with PO-002. All line items match exactly in quantity, price, and description.'
            },
            {
                'LogId': str(uuid.uuid4()),
                'Timestamp': (base_time + timedelta(minutes=3)).isoformat() + 'Z',
                'Actor': 'system',
                'ActionType': 'InvoiceApproved',
                'EntityType': 'Invoice',
                'EntityId': invoice_ids[1],
                'Details': {
                    'autoApproved': True,
                    'reason': 'Perfect match with no discrepancies or fraud flags'
                },
                'Reasoning': 'Auto-approved: Perfect match with PO, no discrepancies, no fraud flags. Confidence: 100%'
            }
        ])
    
    # Invoice 3 - Fraud detected
    if len(invoice_ids) > 2:
        base_time = datetime.now() - timedelta(minutes=30)
        
        audit_logs.extend([
            {
                'LogId': str(uuid.uuid4()),
                'Timestamp': (base_time).isoformat() + 'Z',
                'Actor': 'system',
                'ActionType': 'InvoiceReceived',
                'EntityType': 'Invoice',
                'EntityId': invoice_ids[2],
                'Details': {
                    'invoiceNumber': 'INV-2024-003',
                    'vendorName': 'Unknown Vendor LLC',
                    'totalAmount': '5000.00',
                    'source': 'email'
                }
            },
            {
                'LogId': str(uuid.uuid4()),
                'Timestamp': (base_time + timedelta(minutes=1)).isoformat() + 'Z',
                'Actor': 'system',
                'ActionType': 'InvoiceExtracted',
                'EntityType': 'Invoice',
                'EntityId': invoice_ids[2],
                'Details': {
                    'extractedFields': ['vendorName', 'invoiceNumber', 'totalAmount', 'lineItems'],
                    'confidence': Decimal('0.92')
                },
                'Reasoning': 'PDF extraction completed. Vendor name not recognized in system.'
            },
            {
                'LogId': str(uuid.uuid4()),
                'Timestamp': (base_time + timedelta(minutes=2)).isoformat() + 'Z',
                'Actor': 'system',
                'ActionType': 'FraudDetected',
                'EntityType': 'Invoice',
                'EntityId': invoice_ids[2],
                'Details': {
                    'fraudFlags': ['UNRECOGNIZED_VENDOR'],
                    'riskScore': Decimal('0.85'),
                    'flagDetails': {
                        'vendorName': 'Unknown Vendor LLC',
                        'knownVendors': ['Acme Corp', 'Tech Supplies Inc', 'Office Depot']
                    }
                },
                'Reasoning': 'FRAUD ALERT: Unrecognized vendor detected. Vendor "Unknown Vendor LLC" is not in approved vendor list. High risk score (0.85). Requires immediate review.'
            }
        ])
    
    # Add some PO upload logs
    pos_table = dynamodb.Table('ReconcileAI-POs')
    pos_response = pos_table.scan()
    pos = pos_response.get('Items', [])
    
    if pos:
        for i, po in enumerate(pos[:3]):
            audit_logs.append({
                'LogId': str(uuid.uuid4()),
                'Timestamp': (datetime.now() - timedelta(days=i+1)).isoformat() + 'Z',
                'Actor': '24d82498-2041-7063-6672-c513e9230737',
                'ActionType': 'POUploaded',
                'EntityType': 'PO',
                'EntityId': po['POId'],
                'Details': {
                    'poNumber': po['PONumber'],
                    'vendorName': po['VendorName'],
                    'totalAmount': str(po['TotalAmount']),
                    'lineItemCount': len(po['LineItems']),
                    'uploadedBy': 'admin@reconcileai.com'
                }
            })
    
    print(f"Creating {len(audit_logs)} test audit logs in {AUDIT_LOGS_TABLE}...")
    
    for log in audit_logs:
        try:
            table.put_item(Item=log)
            print(f"✓ Created audit log: {log['ActionType']} for {log['EntityType']} {log['EntityId'][:8]}...")
        except Exception as e:
            print(f"✗ Failed to create audit log: {e}")
    
    print(f"\nTest audit logs created successfully!")
    print(f"\nYou can now:")
    print("1. View audit trail in the frontend at http://localhost:3000")
    print("2. Filter by entity ID, actor, or action type")
    print("3. Export audit logs to CSV")

if __name__ == '__main__':
    create_test_audit_logs()
