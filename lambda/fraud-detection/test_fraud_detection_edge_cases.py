"""
Unit Tests for Fraud Detection Edge Cases
Tests specific edge cases for fraud detection functionality.
"""

import pytest
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

from index import (
    check_price_spikes,
    check_unrecognized_vendor,
    check_duplicate_invoice,
    check_amount_exceedance,
    calculate_risk_score
)


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


def test_invoice_with_multiple_fraud_flags():
    """
    Test invoice with multiple fraud flags (price spike + duplicate + amount exceedance).
    **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
    """
    # Set up mock DynamoDB
    invoices_table, pos_table = setup_dynamodb_tables()
    
    vendor_name = "Test Vendor Inc"
    invoice_number = "INV-DUPLICATE"
    
    # Create historical invoice with same invoice number (for duplicate detection)
    historical_invoice = {
        'InvoiceId': 'hist-001',
        'VendorName': vendor_name,
        'InvoiceNumber': invoice_number,
        'InvoiceDate': '2023-12-15',
        'LineItems': [
            {
                'item_description': 'Widget Pro',
                'quantity': 1,
                'unit_price': Decimal('100.00'),
                'total_price': Decimal('100.00')
            }
        ],
        'TotalAmount': Decimal('100.00'),
        'Status': 'APPROVED',
        'ReceivedDate': '2023-12-15T10:00:00Z',
        'S3Key': 'invoices/2023/12/hist-001.pdf',
        'MatchedPOIds': [],
        'Discrepancies': [],
        'FraudFlags': [],
        'AIReasoning': ''
    }
    invoices_table.put_item(Item=historical_invoice)
    
    # Create PO with lower total (for amount exceedance detection)
    po = {
        'POId': 'po-001',
        'VendorName': vendor_name,
        'PONumber': 'PO-0001',
        'LineItems': [
            {
                'ItemDescription': 'Widget Pro',
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
    
    # Create current invoice with multiple fraud indicators
    current_invoice = {
        'InvoiceId': 'current-001',
        'VendorName': vendor_name,
        'InvoiceNumber': invoice_number,  # Duplicate
        'InvoiceDate': '2024-01-15',
        'LineItems': [
            {
                'item_description': 'Widget Pro',
                'quantity': 1,
                'unit_price': Decimal('150.00'),  # 50% price spike
                'total_price': Decimal('150.00')
            }
        ],
        'TotalAmount': Decimal('150.00'),  # 50% over PO total
        'Status': 'MATCHING',
        'ReceivedDate': '2024-01-15T10:00:00Z',
        'S3Key': 'invoices/2024/01/current.pdf',
        'MatchedPOIds': ['po-001'],
        'Discrepancies': [],
        'FraudFlags': [],
        'AIReasoning': ''
    }
    
    # Reinitialize module's table references
    import index
    index.invoices_table = invoices_table
    index.pos_table = pos_table
    
    # Run all fraud detection checks
    price_spike_flags = check_price_spikes(current_invoice)
    duplicate_flag = check_duplicate_invoice(current_invoice)
    amount_exceedance_flag = check_amount_exceedance(current_invoice)
    
    # Assertions
    assert len(price_spike_flags) > 0, "Expected price spike flag"
    assert duplicate_flag is not None, "Expected duplicate invoice flag"
    assert amount_exceedance_flag is not None, "Expected amount exceedance flag"
    
    # Verify flag types
    assert price_spike_flags[0]['flag_type'] == 'PRICE_SPIKE'
    assert duplicate_flag['flag_type'] == 'DUPLICATE_INVOICE'
    assert amount_exceedance_flag['flag_type'] == 'AMOUNT_EXCEEDED'
    
    # Calculate risk score with multiple flags
    all_flags = price_spike_flags + [duplicate_flag, amount_exceedance_flag]
    risk_score = calculate_risk_score(all_flags)
    
    # Risk score should be high with multiple flags
    assert risk_score >= 90, f"Expected high risk score with multiple flags, got {risk_score}"


def test_invoice_with_no_historical_data():
    """
    Test invoice from vendor with no historical data.
    Should not flag price spikes (no baseline).
    **Validates: Requirements 7.1, 7.2**
    """
    # Set up mock DynamoDB
    invoices_table, pos_table = setup_dynamodb_tables()
    
    vendor_name = "Brand New Vendor"
    
    # Create PO for vendor (so it's not unrecognized)
    po = {
        'POId': 'po-001',
        'VendorName': vendor_name,
        'PONumber': 'PO-0001',
        'LineItems': [
            {
                'ItemDescription': 'New Product',
                'Quantity': 1,
                'UnitPrice': Decimal('1000.00'),
                'TotalPrice': Decimal('1000.00')
            }
        ],
        'TotalAmount': Decimal('1000.00'),
        'UploadDate': '2024-01-01T10:00:00Z',
        'UploadedBy': 'test-user',
        'Status': 'ACTIVE'
    }
    pos_table.put_item(Item=po)
    
    # Create first invoice from this vendor (no historical data)
    invoice = {
        'InvoiceId': 'first-invoice',
        'VendorName': vendor_name,
        'InvoiceNumber': 'INV-001',
        'InvoiceDate': '2024-01-15',
        'LineItems': [
            {
                'item_description': 'New Product',
                'quantity': 1,
                'unit_price': Decimal('1000.00'),
                'total_price': Decimal('1000.00')
            }
        ],
        'TotalAmount': Decimal('1000.00'),
        'Status': 'MATCHING',
        'ReceivedDate': '2024-01-15T10:00:00Z',
        'S3Key': 'invoices/2024/01/first.pdf',
        'MatchedPOIds': ['po-001'],
        'Discrepancies': [],
        'FraudFlags': [],
        'AIReasoning': ''
    }
    
    # Reinitialize module's table references
    import index
    index.invoices_table = invoices_table
    index.pos_table = pos_table
    
    # Run fraud detection checks
    price_spike_flags = check_price_spikes(invoice)
    unrecognized_vendor_flag = check_unrecognized_vendor(invoice)
    
    # Assertions
    assert len(price_spike_flags) == 0, "Should not flag price spikes without historical data"
    assert unrecognized_vendor_flag is None, "Should not flag recognized vendor"


def test_duplicate_invoice_same_vendor_different_number():
    """
    Test that invoices with different numbers from same vendor are not flagged as duplicates.
    """
    # Set up mock DynamoDB
    invoices_table, pos_table = setup_dynamodb_tables()
    
    vendor_name = "Test Vendor Inc"
    
    # Create historical invoice
    historical_invoice = {
        'InvoiceId': 'hist-001',
        'VendorName': vendor_name,
        'InvoiceNumber': 'INV-001',
        'InvoiceDate': '2023-12-15',
        'LineItems': [
            {
                'item_description': 'Widget',
                'quantity': 1,
                'unit_price': Decimal('100.00'),
                'total_price': Decimal('100.00')
            }
        ],
        'TotalAmount': Decimal('100.00'),
        'Status': 'APPROVED',
        'ReceivedDate': '2023-12-15T10:00:00Z',
        'S3Key': 'invoices/2023/12/hist-001.pdf',
        'MatchedPOIds': [],
        'Discrepancies': [],
        'FraudFlags': [],
        'AIReasoning': ''
    }
    invoices_table.put_item(Item=historical_invoice)
    
    # Create current invoice with different number
    current_invoice = {
        'InvoiceId': 'current-001',
        'VendorName': vendor_name,
        'InvoiceNumber': 'INV-002',  # Different number
        'InvoiceDate': '2024-01-15',
        'LineItems': [
            {
                'item_description': 'Widget',
                'quantity': 1,
                'unit_price': Decimal('100.00'),
                'total_price': Decimal('100.00')
            }
        ],
        'TotalAmount': Decimal('100.00'),
        'Status': 'MATCHING',
        'ReceivedDate': '2024-01-15T10:00:00Z',
        'S3Key': 'invoices/2024/01/current.pdf',
        'MatchedPOIds': [],
        'Discrepancies': [],
        'FraudFlags': [],
        'AIReasoning': ''
    }
    
    # Reinitialize module's table references
    import index
    index.invoices_table = invoices_table
    
    # Run duplicate detection
    duplicate_flag = check_duplicate_invoice(current_invoice)
    
    # Assertion
    assert duplicate_flag is None, "Should not flag invoices with different numbers as duplicates"


def test_amount_exceedance_no_matched_pos():
    """
    Test that amount exceedance check handles invoices with no matched POs gracefully.
    """
    # Set up mock DynamoDB
    invoices_table, pos_table = setup_dynamodb_tables()
    
    # Create invoice with no matched POs
    invoice = {
        'InvoiceId': 'test-invoice',
        'VendorName': 'Test Vendor',
        'InvoiceNumber': 'INV-001',
        'InvoiceDate': '2024-01-15',
        'LineItems': [
            {
                'item_description': 'Widget',
                'quantity': 1,
                'unit_price': Decimal('1000.00'),
                'total_price': Decimal('1000.00')
            }
        ],
        'TotalAmount': Decimal('1000.00'),
        'Status': 'MATCHING',
        'ReceivedDate': '2024-01-15T10:00:00Z',
        'S3Key': 'invoices/2024/01/test.pdf',
        'MatchedPOIds': [],  # No matched POs
        'Discrepancies': [],
        'FraudFlags': [],
        'AIReasoning': ''
    }
    
    # Reinitialize module's table references
    import index
    index.pos_table = pos_table
    
    # Run amount exceedance check
    amount_exceedance_flag = check_amount_exceedance(invoice)
    
    # Assertion
    assert amount_exceedance_flag is None, "Should not flag amount exceedance without matched POs"


def test_risk_score_calculation():
    """
    Test risk score calculation with different severity levels.
    """
    # Test with no flags
    assert calculate_risk_score([]) == 0
    
    # Test with single HIGH severity flag
    high_flag = {'flag_type': 'UNRECOGNIZED_VENDOR', 'severity': 'HIGH'}
    assert calculate_risk_score([high_flag]) == 40
    
    # Test with single MEDIUM severity flag
    medium_flag = {'flag_type': 'PRICE_SPIKE', 'severity': 'MEDIUM'}
    assert calculate_risk_score([medium_flag]) == 25
    
    # Test with single LOW severity flag
    low_flag = {'flag_type': 'MINOR_ISSUE', 'severity': 'LOW'}
    assert calculate_risk_score([low_flag]) == 10
    
    # Test with multiple flags (should cap at 100)
    multiple_flags = [
        {'flag_type': 'UNRECOGNIZED_VENDOR', 'severity': 'HIGH'},
        {'flag_type': 'DUPLICATE_INVOICE', 'severity': 'HIGH'},
        {'flag_type': 'PRICE_SPIKE', 'severity': 'MEDIUM'},
        {'flag_type': 'AMOUNT_EXCEEDED', 'severity': 'MEDIUM'}
    ]
    risk_score = calculate_risk_score(multiple_flags)
    assert risk_score == 100, f"Risk score should be capped at 100, got {risk_score}"


def test_amount_exceedance_within_tolerance():
    """
    Test that invoices within 10% of PO total are not flagged.
    """
    # Set up mock DynamoDB
    invoices_table, pos_table = setup_dynamodb_tables()
    
    vendor_name = "Test Vendor Inc"
    
    # Create PO
    po = {
        'POId': 'po-001',
        'VendorName': vendor_name,
        'PONumber': 'PO-0001',
        'LineItems': [
            {
                'ItemDescription': 'Widget',
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
    
    # Create invoice with 9% exceedance (within tolerance)
    invoice = {
        'InvoiceId': 'test-invoice',
        'VendorName': vendor_name,
        'InvoiceNumber': 'INV-001',
        'InvoiceDate': '2024-01-15',
        'LineItems': [
            {
                'item_description': 'Widget',
                'quantity': 1,
                'unit_price': Decimal('109.00'),
                'total_price': Decimal('109.00')
            }
        ],
        'TotalAmount': Decimal('109.00'),  # 9% over PO total
        'Status': 'MATCHING',
        'ReceivedDate': '2024-01-15T10:00:00Z',
        'S3Key': 'invoices/2024/01/test.pdf',
        'MatchedPOIds': ['po-001'],
        'Discrepancies': [],
        'FraudFlags': [],
        'AIReasoning': ''
    }
    
    # Reinitialize module's table references
    import index
    index.pos_table = pos_table
    
    # Run amount exceedance check
    amount_exceedance_flag = check_amount_exceedance(invoice)
    
    # Assertion
    assert amount_exceedance_flag is None, "Should not flag amount exceedance within 10% tolerance"
