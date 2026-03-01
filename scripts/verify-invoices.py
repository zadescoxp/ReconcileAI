#!/usr/bin/env python3
"""
Verify invoices exist in DynamoDB
"""
import boto3
import json
from decimal import Decimal

# Configuration
REGION = 'us-east-1'
INVOICES_TABLE = 'ReconcileAI-Invoices'

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def verify_invoices():
    """Verify invoices in DynamoDB"""
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table = dynamodb.Table(INVOICES_TABLE)
    
    print(f"Scanning {INVOICES_TABLE} table...")
    
    response = table.scan()
    invoices = response.get('Items', [])
    
    print(f"\nFound {len(invoices)} invoices:\n")
    
    for invoice in invoices:
        print(f"Invoice ID: {invoice.get('InvoiceId')}")
        print(f"  Number: {invoice.get('InvoiceNumber')}")
        print(f"  Vendor: {invoice.get('VendorName')}")
        print(f"  Status: {invoice.get('Status')}")
        print(f"  Amount: ${invoice.get('TotalAmount')}")
        print(f"  Date: {invoice.get('InvoiceDate')}")
        print()
    
    # Test the StatusIndex GSI
    print("\nTesting StatusIndex GSI for 'Flagged' status...")
    try:
        response = table.query(
            IndexName='StatusIndex',
            KeyConditionExpression='#status = :status',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={':status': 'Flagged'}
        )
        flagged = response.get('Items', [])
        print(f"Found {len(flagged)} flagged invoices via GSI")
    except Exception as e:
        print(f"Error querying StatusIndex: {e}")
    
    # Test the VendorNameIndex GSI
    print("\nTesting VendorNameIndex GSI for 'Acme Corp'...")
    try:
        response = table.query(
            IndexName='VendorNameIndex',
            KeyConditionExpression='VendorName = :vendor',
            ExpressionAttributeValues={':vendor': 'Acme Corp'}
        )
        acme_invoices = response.get('Items', [])
        print(f"Found {len(acme_invoices)} Acme Corp invoices via GSI")
    except Exception as e:
        print(f"Error querying VendorNameIndex: {e}")

if __name__ == '__main__':
    verify_invoices()
