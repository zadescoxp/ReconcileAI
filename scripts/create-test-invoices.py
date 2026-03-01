#!/usr/bin/env python3
"""
Create test invoices in DynamoDB for ReconcileAI testing
"""
import boto3
from decimal import Decimal
from datetime import datetime, timedelta
import uuid

# Configuration
REGION = 'us-east-1'
INVOICES_TABLE = 'ReconcileAI-Invoices'

def create_test_invoices():
    """Create test invoices in DynamoDB"""
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table = dynamodb.Table(INVOICES_TABLE)
    
    # Test Invoice 1: Flagged with discrepancies
    invoice1 = {
        'InvoiceId': str(uuid.uuid4()),
        'VendorName': 'Acme Corp',
        'InvoiceNumber': 'INV-2024-001',
        'InvoiceDate': (datetime.now() - timedelta(days=5)).isoformat(),
        'ReceivedDate': datetime.now().isoformat(),
        'TotalAmount': Decimal('1250.00'),
        'Status': 'Flagged',
        'S3Key': 'invoices/test-invoice-001.pdf',
        'MatchedPOIds': ['po-001'],
        'LineItems': [
            {
                'LineNumber': 1,
                'ItemDescription': 'Office Chairs',
                'Quantity': Decimal('10'),
                'UnitPrice': Decimal('125.00'),
                'TotalPrice': Decimal('1250.00')
            }
        ],
        'Discrepancies': [
            {
                'type': 'PRICE_MISMATCH',
                'description': 'Invoice price $125.00 exceeds PO price $100.00 by $25.00',
                'difference': Decimal('250.00'),
                'invoiceLine': {
                    'LineNumber': 1,
                    'ItemDescription': 'Office Chairs',
                    'Quantity': Decimal('10'),
                    'UnitPrice': Decimal('125.00'),
                    'TotalPrice': Decimal('1250.00')
                },
                'poLine': {
                    'LineNumber': 1,
                    'ItemDescription': 'Office Chairs',
                    'Quantity': Decimal('10'),
                    'UnitPrice': Decimal('100.00'),
                    'TotalPrice': Decimal('1000.00')
                }
            }
        ],
        'FraudFlags': [],
        'AIReasoning': 'Price discrepancy detected: Invoice unit price ($125.00) exceeds PO unit price ($100.00) by 25%. This requires human review.'
    }
    
    # Test Invoice 2: Approved
    invoice2 = {
        'InvoiceId': str(uuid.uuid4()),
        'VendorName': 'Tech Supplies Inc',
        'InvoiceNumber': 'INV-2024-002',
        'InvoiceDate': (datetime.now() - timedelta(days=3)).isoformat(),
        'ReceivedDate': datetime.now().isoformat(),
        'TotalAmount': Decimal('500.00'),
        'Status': 'Approved',
        'S3Key': 'invoices/test-invoice-002.pdf',
        'MatchedPOIds': ['po-002'],
        'LineItems': [
            {
                'LineNumber': 1,
                'ItemDescription': 'USB Cables',
                'Quantity': Decimal('50'),
                'UnitPrice': Decimal('10.00'),
                'TotalPrice': Decimal('500.00')
            }
        ],
        'Discrepancies': [],
        'FraudFlags': [],
        'AIReasoning': 'Perfect match with PO-002. All line items match exactly. Auto-approved.',
        'ApprovedBy': 'system',
        'ApprovedDate': datetime.now().isoformat()
    }
    
    # Test Invoice 3: Flagged with fraud flags
    invoice3 = {
        'InvoiceId': str(uuid.uuid4()),
        'VendorName': 'Unknown Vendor LLC',
        'InvoiceNumber': 'INV-2024-003',
        'InvoiceDate': (datetime.now() - timedelta(days=1)).isoformat(),
        'ReceivedDate': datetime.now().isoformat(),
        'TotalAmount': Decimal('5000.00'),
        'Status': 'Flagged',
        'S3Key': 'invoices/test-invoice-003.pdf',
        'MatchedPOIds': [],
        'LineItems': [
            {
                'LineNumber': 1,
                'ItemDescription': 'Consulting Services',
                'Quantity': Decimal('1'),
                'UnitPrice': Decimal('5000.00'),
                'TotalPrice': Decimal('5000.00')
            }
        ],
        'Discrepancies': [],
        'FraudFlags': [
            {
                'flagType': 'UNRECOGNIZED_VENDOR',
                'severity': 'HIGH',
                'description': 'Vendor "Unknown Vendor LLC" is not in the approved vendor list',
                'evidence': {
                    'vendorName': 'Unknown Vendor LLC',
                    'knownVendors': ['Acme Corp', 'Tech Supplies Inc', 'Office Depot']
                }
            }
        ],
        'AIReasoning': 'FRAUD ALERT: Unrecognized vendor detected. This vendor is not in our approved vendor list and requires immediate review.'
    }
    
    invoices = [invoice1, invoice2, invoice3]
    
    print(f"Creating {len(invoices)} test invoices in {INVOICES_TABLE}...")
    
    for invoice in invoices:
        try:
            table.put_item(Item=invoice)
            print(f"✓ Created invoice: {invoice['InvoiceNumber']} ({invoice['Status']})")
        except Exception as e:
            print(f"✗ Failed to create invoice {invoice['InvoiceNumber']}: {e}")
    
    print("\nTest invoices created successfully!")
    print("\nYou can now:")
    print("1. View invoices in the frontend at http://localhost:3000")
    print("2. Test the invoice approval workflow")
    print("3. Check the audit trail")

if __name__ == '__main__':
    create_test_invoices()
