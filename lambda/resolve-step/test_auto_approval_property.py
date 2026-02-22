"""
Property Test: Auto-Approval for Clean Invoices
Feature: reconcile-ai, Property 25: Auto-Approval for Clean Invoices

Validates: Requirements 9.1

Property: For any invoice with zero discrepancies and zero fraud flags,
the system should automatically approve it without human intervention.
"""

import pytest
import json
import os
import boto3
from moto import mock_aws
from hypothesis import given, strategies as st, settings
from decimal import Decimal
from datetime import datetime
import uuid

# Set AWS region for tests
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Import the Lambda handler
import sys
sys.path.insert(0, os.path.dirname(__file__))


# Strategy for generating clean invoices (no discrepancies, no fraud flags)
@st.composite
def clean_invoice_event(draw):
    """Generate an event for a clean invoice with no issues"""
    invoice_id = f"INV-{draw(st.integers(min_value=1000, max_value=9999))}"
    
    return {
        'invoice_id': invoice_id,
        'discrepancies': [],  # No discrepancies
        'fraud_flags': [],    # No fraud flags
        'vendor_name': draw(st.text(min_size=3, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters=' '))),
        'invoice_number': f"INV-{draw(st.integers(min_value=1000, max_value=99999))}",
        'total_amount': float(draw(st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False))),
    }


@mock_aws
@given(event=clean_invoice_event())
@settings(max_examples=100, deadline=None)
def test_auto_approval_for_clean_invoices(event):
    """
    Property 25: For any invoice with zero discrepancies and zero fraud flags,
    the system should automatically approve it without human intervention.
    
    **Validates: Requirements 9.1**
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
    # 1. Invoice should be automatically approved
    assert result['status'] == 'Approved', \
        f"Expected status 'Approved' for clean invoice, got '{result['status']}'"
    
    # 2. Should not require human review
    assert result['requires_review'] is False, \
        "Clean invoice should not require human review"
    
    # 3. Reasoning should indicate automatic approval
    assert 'automatically approved' in result['reasoning'].lower(), \
        "Reasoning should indicate automatic approval"
    
    # 4. Discrepancy and fraud flag counts should be zero
    assert result['discrepancy_count'] == 0, \
        f"Expected 0 discrepancies, got {result['discrepancy_count']}"
    assert result['fraud_flag_count'] == 0, \
        f"Expected 0 fraud flags, got {result['fraud_flag_count']}"
    
    # 5. Invoice status in DynamoDB should be updated to "Approved"
    updated_invoice = invoices_table.get_item(Key={'InvoiceId': invoice_id})['Item']
    assert updated_invoice['Status'] == 'Approved', \
        f"Invoice status in DynamoDB should be 'Approved', got '{updated_invoice['Status']}'"
    
    # 6. ApprovedDate should be set
    assert 'ApprovedDate' in updated_invoice, \
        "ApprovedDate should be set for approved invoice"
    
    # 7. Audit log should contain approval entry
    audit_logs = audit_logs_table.scan()['Items']
    approval_logs = [log for log in audit_logs if log['ActionType'] == 'InvoiceApproved' and log['EntityId'] == invoice_id]
    
    assert len(approval_logs) > 0, \
        "Audit log should contain at least one approval entry for this invoice"
    
    approval_log = approval_logs[0]
    assert approval_log['Actor'] == 'System', \
        "Auto-approval should be logged with 'System' as actor"
    assert 'automatic' in approval_log['Details'].get('approval_type', '').lower(), \
        "Audit log should indicate automatic approval"


@mock_aws
def test_auto_approval_edge_case_empty_lists():
    """
    Edge case: Ensure empty lists for discrepancies and fraud_flags
    are treated as clean invoices.
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
    invoice_id = 'INV-EDGE-001'
    invoices_table.put_item(Item={
        'InvoiceId': invoice_id,
        'VendorName': 'Test Vendor',
        'InvoiceNumber': 'TEST-001',
        'TotalAmount': Decimal('1000.00'),
        'Status': 'Detecting',
        'ReceivedDate': datetime.utcnow().isoformat() + 'Z',
    })
    
    # Event with explicitly empty lists
    event = {
        'invoice_id': invoice_id,
        'discrepancies': [],
        'fraud_flags': [],
    }
    
    result = lambda_handler(event, None)
    
    # Should be auto-approved
    assert result['status'] == 'Approved'
    assert result['requires_review'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
