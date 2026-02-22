"""
Property Test: Workflow Pause on Flags
Feature: reconcile-ai, Property 20: Workflow Pause on Flags

Validates: Requirements 7.5, 8.1

Property: For any invoice with at least one discrepancy or fraud flag,
the Step Function should pause and create an approval request rather than auto-approving.
"""

import pytest
import json
import os
import boto3
from moto import mock_aws
from hypothesis import given, strategies as st, settings, assume
from decimal import Decimal
from datetime import datetime
import uuid

# Set AWS region for tests
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Import the Lambda handler
import sys
sys.path.insert(0, os.path.dirname(__file__))


# Strategy for generating flagged invoices (with discrepancies or fraud flags)
@st.composite
def flagged_invoice_event(draw):
    """Generate an event for an invoice with at least one issue"""
    invoice_id = f"INV-{draw(st.integers(min_value=1000, max_value=9999))}"
    
    # Generate at least one discrepancy or fraud flag
    has_discrepancy = draw(st.booleans())
    has_fraud_flag = draw(st.booleans())
    
    # Ensure at least one flag is present
    assume(has_discrepancy or has_fraud_flag)
    
    discrepancies = []
    if has_discrepancy:
        num_discrepancies = draw(st.integers(min_value=1, max_value=5))
        for i in range(num_discrepancies):
            discrepancies.append({
                'type': draw(st.sampled_from(['PRICE_MISMATCH', 'QUANTITY_MISMATCH', 'ITEM_NOT_FOUND'])),
                'description': draw(st.text(min_size=10, max_size=100)),
                'difference': float(draw(st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False))),
            })
    
    fraud_flags = []
    if has_fraud_flag:
        num_flags = draw(st.integers(min_value=1, max_value=3))
        for i in range(num_flags):
            fraud_flags.append({
                'flag_type': draw(st.sampled_from(['PRICE_SPIKE', 'UNRECOGNIZED_VENDOR', 'DUPLICATE_INVOICE', 'AMOUNT_EXCEEDED'])),
                'severity': draw(st.sampled_from(['LOW', 'MEDIUM', 'HIGH'])),
                'description': draw(st.text(min_size=10, max_size=100)),
            })
    
    return {
        'invoice_id': invoice_id,
        'discrepancies': discrepancies,
        'fraud_flags': fraud_flags,
        'vendor_name': draw(st.text(min_size=3, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=' '))),
        'invoice_number': f"INV-{draw(st.integers(min_value=1000, max_value=99999))}",
        'total_amount': float(draw(st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False))),
    }


@mock_aws
@given(event=flagged_invoice_event())
@settings(max_examples=100, deadline=None)
def test_workflow_pause_on_flags(event):
    """
    Property 20: For any invoice with at least one discrepancy or fraud flag,
    the Step Function should pause and create an approval request rather than auto-approving.
    
    **Validates: Requirements 7.5, 8.1**
    """
    
    # Reset global state in Lambda module
    import index
    index._dynamodb = None
    index._invoices_table = None
    index._audit_logs_table = None
    
    # Import handler after reset
    from index import lambda_handler
    
    # Setup mock DynamoDB tables
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    # Create Invoices table
    try:
        invoices_table = dynamodb.create_table(
            TableName='ReconcileAI-Invoices',
            KeySchema=[
                {'AttributeName': 'InvoiceId', 'KeyType': 'HASH'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'InvoiceId', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST'
        )
    except:
        # Table already exists, get it
        invoices_table = dynamodb.Table('ReconcileAI-Invoices')
    
    # Create AuditLogs table
    try:
        audit_logs_table = dynamodb.create_table(
            TableName='ReconcileAI-AuditLogs',
            KeySchema=[
                {'AttributeName': 'LogId', 'KeyType': 'HASH'},
                {'AttributeName': 'Timestamp', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'LogId', 'AttributeType': 'S'},
                {'AttributeName': 'Timestamp', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST'
        )
    except:
        # Table already exists, get it
        audit_logs_table = dynamodb.Table('ReconcileAI-AuditLogs')
    
    # Set environment variables
    os.environ['INVOICES_TABLE_NAME'] = 'ReconcileAI-Invoices'
    os.environ['AUDIT_LOGS_TABLE_NAME'] = 'ReconcileAI-AuditLogs'
    
    # Create invoice in DynamoDB
    invoice_id = event['invoice_id']
    invoices_table.put_item(Item={
        'InvoiceId': invoice_id,
        'VendorName': event['vendor_name'],
        'InvoiceNumber': event['invoice_number'],
        'TotalAmount': Decimal(str(event['total_amount'])),
        'Status': 'Detecting',
        'ReceivedDate': datetime.utcnow().isoformat() + 'Z',
        'MatchedPOIds': [],
    })
    
    # Execute the Lambda handler
    result = lambda_handler(event, None)
    
    # Property assertions
    # 1. Invoice should be flagged for review (not auto-approved)
    assert result['status'] == 'Flagged', \
        f"Expected status 'Flagged' for invoice with issues, got '{result['status']}'"
    
    # 2. Should require human review
    assert result['requires_review'] is True, \
        "Invoice with discrepancies or fraud flags should require human review"
    
    # 3. Reasoning should indicate flagging for review
    assert 'flagged for human review' in result['reasoning'].lower(), \
        "Reasoning should indicate invoice is flagged for human review"
    
    # 4. Discrepancy or fraud flag count should be non-zero
    total_issues = result['discrepancy_count'] + result['fraud_flag_count']
    assert total_issues > 0, \
        f"Expected at least one issue, got {total_issues}"
    
    # 5. Invoice status in DynamoDB should be updated to "Flagged"
    updated_invoice = invoices_table.get_item(Key={'InvoiceId': invoice_id})['Item']
    assert updated_invoice['Status'] == 'Flagged', \
        f"Invoice status in DynamoDB should be 'Flagged', got '{updated_invoice['Status']}'"
    
    # 6. FlaggedDate should be set
    assert 'FlaggedDate' in updated_invoice, \
        "FlaggedDate should be set for flagged invoice"
    
    # 7. Audit log should contain flagging entry
    audit_logs = audit_logs_table.scan()['Items']
    flagging_logs = [log for log in audit_logs if log['ActionType'] == 'InvoiceFlagged' and log['EntityId'] == invoice_id]
    
    assert len(flagging_logs) > 0, \
        "Audit log should contain at least one flagging entry for this invoice"
    
    flagging_log = flagging_logs[0]
    assert flagging_log['Actor'] == 'System', \
        "Flagging should be logged with 'System' as actor"
    
    # 8. Audit log should contain details about discrepancies and fraud flags
    details = flagging_log['Details']
    assert 'discrepancy_count' in details, \
        "Audit log should contain discrepancy count"
    assert 'fraud_flag_count' in details, \
        "Audit log should contain fraud flag count"


@mock_aws
def test_workflow_pause_with_only_discrepancies():
    """
    Edge case: Invoice with only discrepancies (no fraud flags) should still be flagged.
    """
    
    # Reset global state
    import index
    index._dynamodb = None
    index._invoices_table = None
    index._audit_logs_table = None
    
    # Import handler after reset
    from index import lambda_handler
    
    # Setup mock DynamoDB tables
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    invoices_table = dynamodb.create_table(
        TableName='ReconcileAI-Invoices',
        KeySchema=[{'AttributeName': 'InvoiceId', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'InvoiceId', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )
    
    audit_logs_table = dynamodb.create_table(
        TableName='ReconcileAI-AuditLogs',
        KeySchema=[
            {'AttributeName': 'LogId', 'KeyType': 'HASH'},
            {'AttributeName': 'Timestamp', 'KeyType': 'RANGE'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'LogId', 'AttributeType': 'S'},
            {'AttributeName': 'Timestamp', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    os.environ['INVOICES_TABLE_NAME'] = 'ReconcileAI-Invoices'
    os.environ['AUDIT_LOGS_TABLE_NAME'] = 'ReconcileAI-AuditLogs'
    
    # Create invoice
    invoice_id = 'INV-DISC-001'
    invoices_table.put_item(Item={
        'InvoiceId': invoice_id,
        'VendorName': 'Test Vendor',
        'InvoiceNumber': 'TEST-001',
        'TotalAmount': Decimal('1000.00'),
        'Status': 'Detecting',
        'ReceivedDate': datetime.utcnow().isoformat() + 'Z',
    })
    
    # Event with only discrepancies
    event = {
        'invoice_id': invoice_id,
        'discrepancies': [
            {'type': 'PRICE_MISMATCH', 'description': 'Price differs by $50', 'difference': 50.0}
        ],
        'fraud_flags': [],
    }
    
    result = lambda_handler(event, None)
    
    # Should be flagged for review
    assert result['status'] == 'Flagged'
    assert result['requires_review'] is True
    assert result['discrepancy_count'] == 1
    assert result['fraud_flag_count'] == 0


@mock_aws
def test_workflow_pause_with_only_fraud_flags():
    """
    Edge case: Invoice with only fraud flags (no discrepancies) should still be flagged.
    """
    
    # Reset global state
    import index
    index._dynamodb = None
    index._invoices_table = None
    index._audit_logs_table = None
    
    # Import handler after reset
    from index import lambda_handler
    
    # Setup mock DynamoDB tables
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    invoices_table = dynamodb.create_table(
        TableName='ReconcileAI-Invoices',
        KeySchema=[{'AttributeName': 'InvoiceId', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'InvoiceId', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )
    
    audit_logs_table = dynamodb.create_table(
        TableName='ReconcileAI-AuditLogs',
        KeySchema=[
            {'AttributeName': 'LogId', 'KeyType': 'HASH'},
            {'AttributeName': 'Timestamp', 'KeyType': 'RANGE'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'LogId', 'AttributeType': 'S'},
            {'AttributeName': 'Timestamp', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    os.environ['INVOICES_TABLE_NAME'] = 'ReconcileAI-Invoices'
    os.environ['AUDIT_LOGS_TABLE_NAME'] = 'ReconcileAI-AuditLogs'
    
    # Create invoice
    invoice_id = 'INV-FRAUD-001'
    invoices_table.put_item(Item={
        'InvoiceId': invoice_id,
        'VendorName': 'Test Vendor',
        'InvoiceNumber': 'TEST-001',
        'TotalAmount': Decimal('1000.00'),
        'Status': 'Detecting',
        'ReceivedDate': datetime.utcnow().isoformat() + 'Z',
    })
    
    # Event with only fraud flags
    event = {
        'invoice_id': invoice_id,
        'discrepancies': [],
        'fraud_flags': [
            {'flag_type': 'PRICE_SPIKE', 'severity': 'HIGH', 'description': 'Price 50% above average'}
        ],
    }
    
    result = lambda_handler(event, None)
    
    # Should be flagged for review
    assert result['status'] == 'Flagged'
    assert result['requires_review'] is True
    assert result['discrepancy_count'] == 0
    assert result['fraud_flag_count'] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
