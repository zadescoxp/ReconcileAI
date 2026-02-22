"""
Property-Based Test for Price Spike Detection
Feature: reconcile-ai, Property 16: Price Spike Detection
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
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

from index import check_price_spikes, get_historical_invoices


# Global table reference to avoid recreating
_invoices_table = None


def setup_dynamodb_tables():
    """Set up mock DynamoDB tables for testing."""
    global _invoices_table
    
    if _invoices_table is not None:
        # Clear existing data
        scan_response = _invoices_table.scan()
        for item in scan_response.get('Items', []):
            _invoices_table.delete_item(Key={'InvoiceId': item['InvoiceId']})
        return _invoices_table
    
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    # Create Invoices table
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
    
    return _invoices_table


@given(
    base_price=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    price_increase_factor=st.floats(min_value=1.21, max_value=3.0, allow_nan=False, allow_infinity=False),
    historical_count=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_price_spike_detection_property(base_price, price_increase_factor, historical_count):
    """
    Property 16: For any invoice line item where the price exceeds the historical 
    average for the same vendor and item by more than 20%, the system should flag 
    it with a PRICE_SPIKE fraud flag.
    
    **Validates: Requirements 7.1**
    """
    # Set up mock DynamoDB
    invoices_table = setup_dynamodb_tables()
    
    # Generate test data
    vendor_name = "Test Vendor Inc"
    item_description = "Widget Pro 3000"
    
    # Create historical invoices with consistent pricing
    historical_invoices = []
    for i in range(historical_count):
        # Add some variance to historical prices (±5%)
        variance = 1.0 + (i % 3 - 1) * 0.05
        hist_price = float(Decimal(str(base_price)) * Decimal(str(variance)))
        
        hist_invoice = {
            'InvoiceId': f'hist-{i}',
            'VendorName': vendor_name,
            'InvoiceNumber': f'HIST-{i}',
            'InvoiceDate': f'2023-{(i % 12) + 1:02d}-15',
            'LineItems': [
                {
                    'item_description': item_description,
                    'quantity': 1,
                    'unit_price': Decimal(str(hist_price)),
                    'total_price': Decimal(str(hist_price))
                }
            ],
            'TotalAmount': Decimal(str(hist_price)),
            'Status': 'APPROVED',
            'ReceivedDate': f'2023-{(i % 12) + 1:02d}-15T10:00:00Z',
            'S3Key': f'invoices/2023/{(i % 12) + 1:02d}/hist-{i}.pdf',
            'MatchedPOIds': [],
            'Discrepancies': [],
            'FraudFlags': [],
            'AIReasoning': ''
        }
        historical_invoices.append(hist_invoice)
        invoices_table.put_item(Item=hist_invoice)
    
    # Calculate historical average
    historical_avg = base_price  # Approximately, given the small variance
    
    # Create current invoice with price spike (>20% increase)
    spiked_price = float(Decimal(str(base_price)) * Decimal(str(price_increase_factor)))
    current_invoice = {
        'InvoiceId': 'current-invoice',
        'VendorName': vendor_name,
        'InvoiceNumber': 'CURRENT-001',
        'InvoiceDate': '2024-01-15',
        'LineItems': [
            {
                'item_description': item_description,
                'quantity': 1,
                'unit_price': Decimal(str(spiked_price)),
                'total_price': Decimal(str(spiked_price))
            }
        ],
        'TotalAmount': Decimal(str(spiked_price)),
        'Status': 'MATCHING',
        'ReceivedDate': '2024-01-15T10:00:00Z',
        'S3Key': 'invoices/2024/01/current.pdf',
        'MatchedPOIds': [],
        'Discrepancies': [],
        'FraudFlags': [],
        'AIReasoning': ''
    }
    
    # Reinitialize the module's table reference to use mocked table
    import index
    index.invoices_table = invoices_table
    
    # Run price spike detection
    fraud_flags = check_price_spikes(current_invoice)
    
    # Property assertion: Since price increased by >20%, should have PRICE_SPIKE flag
    price_spike_flags = [f for f in fraud_flags if f['flag_type'] == 'PRICE_SPIKE']
    
    assert len(price_spike_flags) > 0, \
        f"Expected PRICE_SPIKE flag for {spiked_price:.2f} vs historical avg ~{historical_avg:.2f} " \
        f"(increase factor {price_increase_factor:.2f}), but got {len(price_spike_flags)} flags"
    
    # Verify flag details
    flag = price_spike_flags[0]
    assert flag['flag_type'] == 'PRICE_SPIKE'
    assert flag['severity'] in ['LOW', 'MEDIUM', 'HIGH']
    assert 'evidence' in flag
    assert flag['evidence']['item_description'] == item_description
    assert flag['evidence']['current_price'] == spiked_price


@given(
    base_price=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    price_change_factor=st.floats(min_value=0.8, max_value=1.20, allow_nan=False, allow_infinity=False),
    historical_count=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_no_price_spike_within_tolerance(base_price, price_change_factor, historical_count):
    """
    Property: For any invoice line item where the price is within ±20% of the 
    historical average, the system should NOT flag it with a PRICE_SPIKE fraud flag.
    
    This is the inverse property - ensuring we don't have false positives.
    """
    # Set up mock DynamoDB
    invoices_table = setup_dynamodb_tables()
    
    # Generate test data
    vendor_name = "Test Vendor Inc"
    item_description = "Widget Pro 3000"
    
    # Create historical invoices
    for i in range(historical_count):
        variance = 1.0 + (i % 3 - 1) * 0.05
        hist_price = float(Decimal(str(base_price)) * Decimal(str(variance)))
        
        hist_invoice = {
            'InvoiceId': f'hist-{i}',
            'VendorName': vendor_name,
            'InvoiceNumber': f'HIST-{i}',
            'InvoiceDate': f'2023-{(i % 12) + 1:02d}-15',
            'LineItems': [
                {
                    'item_description': item_description,
                    'quantity': 1,
                    'unit_price': Decimal(str(hist_price)),
                    'total_price': Decimal(str(hist_price))
                }
            ],
            'TotalAmount': Decimal(str(hist_price)),
            'Status': 'APPROVED',
            'ReceivedDate': f'2023-{(i % 12) + 1:02d}-15T10:00:00Z',
            'S3Key': f'invoices/2023/{(i % 12) + 1:02d}/hist-{i}.pdf',
            'MatchedPOIds': [],
            'Discrepancies': [],
            'FraudFlags': [],
            'AIReasoning': ''
        }
        invoices_table.put_item(Item=hist_invoice)
    
    # Create current invoice with price within tolerance
    current_price = float(Decimal(str(base_price)) * Decimal(str(price_change_factor)))
    current_invoice = {
        'InvoiceId': 'current-invoice',
        'VendorName': vendor_name,
        'InvoiceNumber': 'CURRENT-001',
        'InvoiceDate': '2024-01-15',
        'LineItems': [
            {
                'item_description': item_description,
                'quantity': 1,
                'unit_price': Decimal(str(current_price)),
                'total_price': Decimal(str(current_price))
            }
        ],
        'TotalAmount': Decimal(str(current_price)),
        'Status': 'MATCHING',
        'ReceivedDate': '2024-01-15T10:00:00Z',
        'S3Key': 'invoices/2024/01/current.pdf',
        'MatchedPOIds': [],
        'Discrepancies': [],
        'FraudFlags': [],
        'AIReasoning': ''
    }
    
    # Reinitialize the module's table reference
    import index
    index.invoices_table = invoices_table
    
    # Run price spike detection
    fraud_flags = check_price_spikes(current_invoice)
    
    # Property assertion: Price within ±20% should NOT have PRICE_SPIKE flag
    price_spike_flags = [f for f in fraud_flags if f['flag_type'] == 'PRICE_SPIKE']
    
    assert len(price_spike_flags) == 0, \
        f"Expected NO PRICE_SPIKE flag for {current_price:.2f} vs historical avg ~{base_price:.2f} " \
        f"(change factor {price_change_factor:.2f}), but got {len(price_spike_flags)} flags"


@pytest.mark.property_test
def test_no_price_spike_without_historical_data():
    """
    Property: For any invoice from a vendor with no historical data, 
    the system should NOT flag price spikes (cannot determine baseline).
    """
    # Set up mock DynamoDB
    invoices_table = setup_dynamodb_tables()
    
    # Create invoice with no historical data
    current_invoice = {
        'InvoiceId': 'first-invoice',
        'VendorName': 'Brand New Vendor',
        'InvoiceNumber': 'FIRST-001',
        'InvoiceDate': '2024-01-15',
        'LineItems': [
            {
                'item_description': 'Expensive Item',
                'quantity': 1,
                'unit_price': Decimal('99999.99'),
                'total_price': Decimal('99999.99')
            }
        ],
        'TotalAmount': Decimal('99999.99'),
        'Status': 'MATCHING',
        'ReceivedDate': '2024-01-15T10:00:00Z',
        'S3Key': 'invoices/2024/01/first.pdf',
        'MatchedPOIds': [],
        'Discrepancies': [],
        'FraudFlags': [],
        'AIReasoning': ''
    }
    
    # Reinitialize the module's table reference
    import index
    index.invoices_table = invoices_table
    
    # Run price spike detection
    fraud_flags = check_price_spikes(current_invoice)
    
    # Property assertion: No historical data means no price spike detection
    price_spike_flags = [f for f in fraud_flags if f['flag_type'] == 'PRICE_SPIKE']
    
    assert len(price_spike_flags) == 0, \
        f"Expected NO PRICE_SPIKE flag without historical data, but got {len(price_spike_flags)} flags"
