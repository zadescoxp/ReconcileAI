"""
Property-Based Test for Unrecognized Vendor Detection
Feature: reconcile-ai, Property 17: Unrecognized Vendor Detection
"""

import pytest
from hypothesis import given, strategies as st, settings
from decimal import Decimal
import sys
import os

# Set up environment before importing index
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['INVOICES_TABLE_NAME'] = 'ReconcileAI-Invoices'
os.environ['POS_TABLE_NAME'] = 'ReconcileAI-POs'
os.environ['AUDIT_LOGS_TABLE_NAME'] = 'ReconcileAI-AuditLogs'

# Mock AWS for testing
import boto3
from moto import mock_aws

# Start mocking before importing index
mock = mock_aws()
mock.start()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from index import check_unrecognized_vendor


# Global table references
_invoices_table = None
_pos_table = None


def setup_dynamodb_tables():
    """Set up mock DynamoDB tables for testing."""
    global _invoices_table, _pos_table
    
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    # Create or clear Invoices table
    if _invoices_table is None:
        _invoices_table = dynamodb.create_table(
            TableName='ReconcileAI-Invoices',
            KeySchema=[
                {'AttributeName': 'InvoiceId', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'InvoiceId', 'AttributeType': 'S'},
                {'AttributeName': 'VendorName', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'VendorNameIndex',
                    'KeySchema': [
                        {'AttributeName': 'VendorName', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
    else:
        # Clear existing data
        scan_response = _invoices_table.scan()
        for item in scan_response.get('Items', []):
            _invoices_table.delete_item(Key={'InvoiceId': item['InvoiceId']})
    
    # Create or clear POs table
    if _pos_table is None:
        _pos_table = dynamodb.create_table(
            TableName='ReconcileAI-POs',
            KeySchema=[
                {'AttributeName': 'POId', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'POId', 'AttributeType': 'S'},
                {'AttributeName': 'VendorName', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'VendorNameIndex',
                    'KeySchema': [
                        {'AttributeName': 'VendorName', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
    else:
        # Clear existing data
        scan_response = _pos_table.scan()
        for item in scan_response.get('Items', []):
            _pos_table.delete_item(Key={'POId': item['POId']})
    
    return _invoices_table, _pos_table


@given(
    vendor_name=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs')))
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_unrecognized_vendor_detection_property(vendor_name):
    """
    Property 17: For any invoice from a vendor with no matching POs in the system,
    the system should flag it with an UNRECOGNIZED_VENDOR fraud flag.
    
    **Validates: Requirements 7.2**
    """
    # Set up mock DynamoDB
    invoices_table, pos_table = setup_dynamodb_tables()
    
    # Create invoice from unrecognized vendor (no POs exist for this vendor)
    invoice = {
        'InvoiceId': 'test-invoice',
        'VendorName': vendor_name,
        'InvoiceNumber': 'INV-001',
        'InvoiceDate': '2024-01-15',
        'LineItems': [
            {
                'item_description': 'Test Item',
                'quantity': 1,
                'unit_price': Decimal('100.00'),
                'total_price': Decimal('100.00')
            }
        ],
        'TotalAmount': Decimal('100.00'),
        'Status': 'MATCHING',
        'ReceivedDate': '2024-01-15T10:00:00Z',
        'S3Key': 'invoices/2024/01/test.pdf',
        'MatchedPOIds': [],
        'Discrepancies': [],
        'FraudFlags': [],
        'AIReasoning': ''
    }
    
    # Reinitialize the module's table references
    import index
    index.pos_table = pos_table
    
    # Run unrecognized vendor detection
    fraud_flag = check_unrecognized_vendor(invoice)
    
    # Property assertion: Vendor with no POs should be flagged
    assert fraud_flag is not None, \
        f"Expected UNRECOGNIZED_VENDOR flag for vendor '{vendor_name}' with no POs"
    
    assert fraud_flag['flag_type'] == 'UNRECOGNIZED_VENDOR'
    assert fraud_flag['severity'] == 'HIGH'
    assert vendor_name in fraud_flag['description']
    assert 'evidence' in fraud_flag
    assert fraud_flag['evidence']['vendor_name'] == vendor_name
    assert fraud_flag['evidence']['po_count'] == 0


@given(
    vendor_name=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs'))),
    po_count=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_recognized_vendor_no_flag(vendor_name, po_count):
    """
    Property: For any invoice from a vendor with at least one PO in the system,
    the system should NOT flag it with an UNRECOGNIZED_VENDOR fraud flag.
    
    This is the inverse property - ensuring we don't have false positives.
    """
    # Set up mock DynamoDB
    invoices_table, pos_table = setup_dynamodb_tables()
    
    # Create POs for this vendor
    for i in range(po_count):
        po = {
            'POId': f'po-{i}',
            'VendorName': vendor_name,
            'PONumber': f'PO-{i:04d}',
            'LineItems': [
                {
                    'ItemDescription': 'Test Item',
                    'Quantity': 1,
                    'UnitPrice': Decimal('100.00'),
                    'TotalPrice': Decimal('100.00')
                }
            ],
            'TotalAmount': Decimal('100.00'),
            'UploadDate': '2024-01-01T10:00:00Z',
            'UploadedBy': 'test-user',
            'Status': 'ACTIVE'
        }
        pos_table.put_item(Item=po)
    
    # Create invoice from recognized vendor
    invoice = {
        'InvoiceId': 'test-invoice',
        'VendorName': vendor_name,
        'InvoiceNumber': 'INV-001',
        'InvoiceDate': '2024-01-15',
        'LineItems': [
            {
                'item_description': 'Test Item',
                'quantity': 1,
                'unit_price': Decimal('100.00'),
                'total_price': Decimal('100.00')
            }
        ],
        'TotalAmount': Decimal('100.00'),
        'Status': 'MATCHING',
        'ReceivedDate': '2024-01-15T10:00:00Z',
        'S3Key': 'invoices/2024/01/test.pdf',
        'MatchedPOIds': [],
        'Discrepancies': [],
        'FraudFlags': [],
        'AIReasoning': ''
    }
    
    # Reinitialize the module's table references
    import index
    index.pos_table = pos_table
    
    # Run unrecognized vendor detection
    fraud_flag = check_unrecognized_vendor(invoice)
    
    # Property assertion: Vendor with POs should NOT be flagged
    assert fraud_flag is None, \
        f"Expected NO UNRECOGNIZED_VENDOR flag for vendor '{vendor_name}' with {po_count} POs, " \
        f"but got flag: {fraud_flag}"


@pytest.mark.property_test
def test_empty_vendor_name_handling():
    """
    Property: The system should handle edge cases like empty vendor names gracefully.
    """
    # Set up mock DynamoDB
    invoices_table, pos_table = setup_dynamodb_tables()
    
    # Create invoice with empty vendor name
    invoice = {
        'InvoiceId': 'test-invoice',
        'VendorName': '',
        'InvoiceNumber': 'INV-001',
        'InvoiceDate': '2024-01-15',
        'LineItems': [
            {
                'item_description': 'Test Item',
                'quantity': 1,
                'unit_price': Decimal('100.00'),
                'total_price': Decimal('100.00')
            }
        ],
        'TotalAmount': Decimal('100.00'),
        'Status': 'MATCHING',
        'ReceivedDate': '2024-01-15T10:00:00Z',
        'S3Key': 'invoices/2024/01/test.pdf',
        'MatchedPOIds': [],
        'Discrepancies': [],
        'FraudFlags': [],
        'AIReasoning': ''
    }
    
    # Reinitialize the module's table references
    import index
    index.pos_table = pos_table
    
    # Run unrecognized vendor detection
    fraud_flag = check_unrecognized_vendor(invoice)
    
    # Should flag empty vendor name as unrecognized
    assert fraud_flag is not None
    assert fraud_flag['flag_type'] == 'UNRECOGNIZED_VENDOR'


@given(
    vendor_name=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs')))
)
@settings(max_examples=50, deadline=None)
@pytest.mark.property_test
def test_case_sensitive_vendor_matching(vendor_name):
    """
    Property: Vendor name matching should be case-sensitive.
    A vendor with different casing should be treated as unrecognized.
    """
    # Set up mock DynamoDB
    invoices_table, pos_table = setup_dynamodb_tables()
    
    # Create PO with original vendor name
    po = {
        'POId': 'po-001',
        'VendorName': vendor_name,
        'PONumber': 'PO-0001',
        'LineItems': [
            {
                'ItemDescription': 'Test Item',
                'Quantity': 1,
                'UnitPrice': Decimal('100.00'),
                'TotalPrice': Decimal('100.00')
            }
        ],
        'TotalAmount': Decimal('100.00'),
        'UploadDate': '2024-01-01T10:00:00Z',
        'UploadedBy': 'test-user',
        'Status': 'ACTIVE'
    }
    pos_table.put_item(Item=po)
    
    # Create invoice with different casing (if possible)
    different_case_vendor = vendor_name.swapcase()
    
    # Only test if casing actually changed
    if different_case_vendor != vendor_name:
        invoice = {
            'InvoiceId': 'test-invoice',
            'VendorName': different_case_vendor,
            'InvoiceNumber': 'INV-001',
            'InvoiceDate': '2024-01-15',
            'LineItems': [
                {
                    'item_description': 'Test Item',
                    'quantity': 1,
                    'unit_price': Decimal('100.00'),
                    'total_price': Decimal('100.00')
                }
            ],
            'TotalAmount': Decimal('100.00'),
            'Status': 'MATCHING',
            'ReceivedDate': '2024-01-15T10:00:00Z',
            'S3Key': 'invoices/2024/01/test.pdf',
            'MatchedPOIds': [],
            'Discrepancies': [],
            'FraudFlags': [],
            'AIReasoning': ''
        }
        
        # Reinitialize the module's table references
        import index
        index.pos_table = pos_table
        
        # Run unrecognized vendor detection
        fraud_flag = check_unrecognized_vendor(invoice)
        
        # Property assertion: Different casing should be treated as unrecognized
        assert fraud_flag is not None, \
            f"Expected UNRECOGNIZED_VENDOR flag for vendor '{different_case_vendor}' " \
            f"(different casing from '{vendor_name}')"
