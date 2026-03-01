#!/usr/bin/env python3
"""
Create test data for ReconcileAI end-to-end testing
"""

import boto3
import json
from datetime import datetime, timedelta, timezone
import uuid
from decimal import Decimal

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1')

# Table names
POS_TABLE = 'ReconcileAI-POs'
INVOICES_TABLE = 'ReconcileAI-Invoices'
BUCKET_NAME = 'reconcileai-invoices-463470938082'

def create_sample_pos():
    """Create sample purchase orders"""
    pos_table = dynamodb.Table(POS_TABLE)
    
    # PO 1: Perfect Match Scenario
    po1_id = f"PO-TEST-001-{int(datetime.now().timestamp())}"
    po1 = {
        'POId': po1_id,
        'VendorName': 'TechSupplies Inc',
        'PONumber': 'PO-2024-001',
        'LineItems': [
            {
                'LineNumber': 1,
                'ItemDescription': 'Laptop Computer - Model X1',
                'Quantity': 5,
                'UnitPrice': Decimal('1200.00'),
                'TotalPrice': Decimal('6000.00'),
                'MatchedQuantity': 0
            },
            {
                'LineNumber': 2,
                'ItemDescription': 'Wireless Mouse',
                'Quantity': 10,
                'UnitPrice': Decimal('25.00'),
                'TotalPrice': Decimal('250.00'),
                'MatchedQuantity': 0
            }
        ],
        'TotalAmount': Decimal('6250.00'),
        'UploadDate': datetime.now(timezone.utc).isoformat(),
        'UploadedBy': 'test-user',
        'Status': 'Active'
    }
    
    # PO 2: Price Discrepancy Scenario
    po2_id = f"PO-TEST-002-{int(datetime.now().timestamp())}"
    po2 = {
        'POId': po2_id,
        'VendorName': 'Office Depot Pro',
        'PONumber': 'PO-2024-002',
        'LineItems': [
            {
                'LineNumber': 1,
                'ItemDescription': 'Office Chair - Ergonomic',
                'Quantity': 20,
                'UnitPrice': Decimal('150.00'),
                'TotalPrice': Decimal('3000.00'),
                'MatchedQuantity': 0
            },
            {
                'LineNumber': 2,
                'ItemDescription': 'Standing Desk',
                'Quantity': 10,
                'UnitPrice': Decimal('400.00'),
                'TotalPrice': Decimal('4000.00'),
                'MatchedQuantity': 0
            }
        ],
        'TotalAmount': Decimal('7000.00'),
        'UploadDate': datetime.now(timezone.utc).isoformat(),
        'UploadedBy': 'test-user',
        'Status': 'Active'
    }
    
    # PO 3: Historical Data for Fraud Detection
    po3_id = f"PO-TEST-003-{int(datetime.now().timestamp())}"
    po3 = {
        'POId': po3_id,
        'VendorName': 'Acme Supplies',
        'PONumber': 'PO-2024-003',
        'LineItems': [
            {
                'LineNumber': 1,
                'ItemDescription': 'Paper Reams - A4',
                'Quantity': 100,
                'UnitPrice': Decimal('5.00'),
                'TotalPrice': Decimal('500.00'),
                'MatchedQuantity': 0
            }
        ],
        'TotalAmount': Decimal('500.00'),
        'UploadDate': (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        'UploadedBy': 'test-user',
        'Status': 'Active'
    }
    
    # Insert POs
    print("Creating sample POs...")
    pos_table.put_item(Item=po1)
    print(f"✓ Created PO: {po1_id} (TechSupplies Inc - $6,250)")
    
    pos_table.put_item(Item=po2)
    print(f"✓ Created PO: {po2_id} (Office Depot Pro - $7,000)")
    
    pos_table.put_item(Item=po3)
    print(f"✓ Created PO: {po3_id} (Acme Supplies - $500)")
    
    return [po1, po2, po3]

def verify_pos():
    """Verify POs were created"""
    pos_table = dynamodb.Table(POS_TABLE)
    
    print("\nVerifying POs in database...")
    response = pos_table.scan(
        FilterExpression='begins_with(POId, :prefix)',
        ExpressionAttributeValues={':prefix': 'PO-TEST'}
    )
    
    print(f"Found {response['Count']} test POs")
    for po in response['Items']:
        print(f"  - {po['PONumber']}: {po['VendorName']} (${po['TotalAmount']})")
    
    return response['Items']

def check_audit_logs():
    """Check if audit logging is working"""
    audit_table = dynamodb.Table('ReconcileAI-AuditLogs')
    
    print("\nChecking audit logs...")
    response = audit_table.scan(Limit=5)
    
    print(f"Total audit log entries: {response['Count']}")
    if response['Count'] > 0:
        print("Recent entries:")
        for log in response['Items'][:3]:
            print(f"  - {log.get('ActionType', 'N/A')} by {log.get('Actor', 'N/A')} at {log.get('Timestamp', 'N/A')}")
    
    return response['Count']

def check_s3_bucket():
    """Check S3 bucket status"""
    print("\nChecking S3 bucket...")
    
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, MaxKeys=10)
        count = response.get('KeyCount', 0)
        print(f"S3 bucket contains {count} objects")
        
        if count > 0:
            print("Recent objects:")
            for obj in response.get('Contents', [])[:3]:
                print(f"  - {obj['Key']} ({obj['Size']} bytes)")
    except Exception as e:
        print(f"Error accessing S3: {e}")

def main():
    print("=" * 50)
    print("ReconcileAI Test Data Creation")
    print("=" * 50)
    print()
    
    # Create sample POs
    pos = create_sample_pos()
    
    # Verify creation
    verify_pos()
    
    # Check audit logs
    check_audit_logs()
    
    # Check S3
    check_s3_bucket()
    
    print()
    print("=" * 50)
    print("Test Data Creation Complete!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("1. Frontend is running at http://localhost:3000")
    print("2. Login with: admin@reconcileai.com")
    print("3. Navigate to PO Management to see test POs")
    print("4. Test invoice upload and processing")
    print()

if __name__ == '__main__':
    main()
