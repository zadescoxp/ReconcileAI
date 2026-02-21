"""
Unit Tests for AI Matching Lambda - Edge Cases
Tests edge cases: no matching POs, multiple matching POs, Bedrock API failures
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import sys
from botocore.exceptions import ClientError

# Set environment variables before importing index
os.environ['POS_TABLE_NAME'] = 'test-pos-table'
os.environ['INVOICES_TABLE_NAME'] = 'test-invoices-table'
os.environ['AUDIT_LOGS_TABLE_NAME'] = 'test-audit-logs-table'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture
def mock_aws_services():
    """Mock all AWS services (DynamoDB and Bedrock)."""
    with patch('boto3.client') as mock_client, \
         patch('boto3.resource') as mock_resource:
        
        # Mock Bedrock client
        mock_bedrock_client = MagicMock()
        
        # Mock DynamoDB resource
        mock_dynamodb_resource = MagicMock()
        mock_pos_table = MagicMock()
        mock_invoices_table = MagicMock()
        mock_audit_logs_table = MagicMock()
        
        # Configure boto3.client to return bedrock client
        mock_client.return_value = mock_bedrock_client
        
        # Configure boto3.resource to return dynamodb resource
        mock_resource.return_value = mock_dynamodb_resource
        
        # Configure Table() to return appropriate table mocks
        def get_table(name):
            if name == 'test-pos-table':
                return mock_pos_table
            elif name == 'test-invoices-table':
                return mock_invoices_table
            elif name == 'test-audit-logs-table':
                return mock_audit_logs_table
            return MagicMock()
        
        mock_dynamodb_resource.Table.side_effect = get_table
        
        # Reload the index module to pick up mocked clients
        if 'index' in sys.modules:
            del sys.modules['index']
        
        yield {
            'bedrock': mock_bedrock_client,
            'pos_table': mock_pos_table,
            'invoices_table': mock_invoices_table,
            'audit_logs_table': mock_audit_logs_table
        }


@pytest.fixture
def sample_invoice():
    """Sample invoice data for testing."""
    return {
        'InvoiceId': 'inv-12345',
        'VendorName': 'Acme Corp',
        'InvoiceNumber': 'INV-001',
        'InvoiceDate': '2024-01-15',
        'LineItems': [
            {
                'item_description': 'Widget A',
                'quantity': 10,
                'unit_price': 25.00,
                'total_price': 250.00
            },
            {
                'item_description': 'Widget B',
                'quantity': 5,
                'unit_price': 50.00,
                'total_price': 250.00
            }
        ],
        'TotalAmount': 500.00,
        'Status': 'EXTRACTING'
    }


@pytest.fixture
def sample_po():
    """Sample PO data for testing."""
    return {
        'POId': 'po-67890',
        'VendorName': 'Acme Corp',
        'PONumber': 'PO-001',
        'LineItems': [
            {
                'ItemDescription': 'Widget A',
                'Quantity': 10,
                'UnitPrice': 25.00,
                'TotalPrice': 250.00
            },
            {
                'ItemDescription': 'Widget B',
                'Quantity': 5,
                'UnitPrice': 50.00,
                'TotalPrice': 250.00
            }
        ],
        'TotalAmount': 500.00
    }


# Edge Case 1: Invoice with no matching POs
def test_invoice_with_no_matching_pos(mock_aws_services, sample_invoice):
    """
    Test that when no POs are found for a vendor, the system handles it gracefully.
    
    Expected behavior:
    - Query returns empty list
    - Match result indicates no POs found
    - Confidence score is 0
    - Reasoning explains no POs found
    - Invoice is not flagged as error (will be caught by fraud detection)
    
    Validates: Requirements 5.1, 5.2
    """
    # Import after mocking
    from index import lambda_handler
    
    # Mock DynamoDB responses
    mock_aws_services['invoices_table'].get_item.return_value = {
        'Item': sample_invoice
    }
    
    # Mock query_relevant_pos to return empty list
    mock_aws_services['pos_table'].query.return_value = {
        'Items': []
    }
    
    # Mock update operations
    mock_aws_services['invoices_table'].update_item.return_value = {}
    mock_aws_services['audit_logs_table'].put_item.return_value = {}
    
    # Execute lambda
    event = {'invoice_id': 'inv-12345'}
    result = lambda_handler(event, None)
    
    # Assertions
    assert result['statusCode'] == 200
    assert result['invoice_id'] == 'inv-12345'
    assert result['matched_po_ids'] == []
    assert result['confidence_score'] == 0
    assert result['is_perfect_match'] is False
    
    # Verify DynamoDB query was called
    mock_aws_services['pos_table'].query.assert_called_once()
    
    # Verify audit log was created
    assert mock_aws_services['audit_logs_table'].put_item.called


# Edge Case 2: Invoice with multiple matching POs
def test_invoice_with_multiple_matching_pos(mock_aws_services, sample_invoice, sample_po):
    """
    Test that when multiple POs match a vendor, the AI can match against all of them.
    
    Expected behavior:
    - Query returns multiple POs
    - All POs are sent to Bedrock for matching
    - AI can match line items across multiple POs
    - Match result includes all matched PO IDs
    
    Validates: Requirements 5.1, 5.2
    """
    # Import after mocking
    from index import lambda_handler
    
    # Create multiple POs
    po1 = sample_po.copy()
    po1['POId'] = 'po-11111'
    po1['PONumber'] = 'PO-001'
    po1['LineItems'] = [sample_po['LineItems'][0]]  # Only first item
    po1['TotalAmount'] = 250.00
    
    po2 = sample_po.copy()
    po2['POId'] = 'po-22222'
    po2['PONumber'] = 'PO-002'
    po2['LineItems'] = [sample_po['LineItems'][1]]  # Only second item
    po2['TotalAmount'] = 250.00
    
    # Mock DynamoDB responses
    mock_aws_services['invoices_table'].get_item.return_value = {
        'Item': sample_invoice
    }
    
    # Mock query to return multiple POs
    mock_aws_services['pos_table'].query.return_value = {
        'Items': [po1, po2]
    }
    
    # Mock Bedrock response indicating matches from both POs
    bedrock_response = {
        'matched_po_ids': ['po-11111', 'po-22222'],
        'line_matches': [
            {
                'invoice_line': 1,
                'po_id': 'po-11111',
                'po_line': 1,
                'match_confidence': 95,
                'discrepancies': []
            },
            {
                'invoice_line': 2,
                'po_id': 'po-22222',
                'po_line': 1,
                'match_confidence': 95,
                'discrepancies': []
            }
        ],
        'overall_confidence': 95,
        'reasoning': 'Invoice line 1 matches PO-001, line 2 matches PO-002',
        'discrepancies': []
    }
    
    mock_aws_services['bedrock'].invoke_model.return_value = {
        'body': MagicMock(read=lambda: json.dumps({
            'content': [{'text': json.dumps(bedrock_response)}]
        }).encode())
    }
    
    # Mock update operations
    mock_aws_services['invoices_table'].update_item.return_value = {}
    mock_aws_services['audit_logs_table'].put_item.return_value = {}
    
    # Execute lambda
    event = {'invoice_id': 'inv-12345'}
    result = lambda_handler(event, None)
    
    # Assertions
    assert result['statusCode'] == 200
    assert result['invoice_id'] == 'inv-12345'
    assert len(result['matched_po_ids']) == 2
    assert 'po-11111' in result['matched_po_ids']
    assert 'po-22222' in result['matched_po_ids']
    assert result['confidence_score'] == 95
    
    # Verify Bedrock was called with both POs
    assert mock_aws_services['bedrock'].invoke_model.called
    call_args = mock_aws_services['bedrock'].invoke_model.call_args
    request_body = json.loads(call_args[1]['body'])
    prompt = request_body['messages'][0]['content']
    assert 'PO-001' in prompt
    assert 'PO-002' in prompt


# Edge Case 3: Bedrock API throttling error
def test_bedrock_api_throttling_error(mock_aws_services, sample_invoice, sample_po):
    """
    Test that Bedrock API throttling errors are handled as retryable errors.
    
    Expected behavior:
    - Bedrock returns ThrottlingException
    - Lambda raises RetryableError
    - Step Functions will retry the operation
    - Error is logged to audit trail
    
    Validates: Requirements 5.1, 5.2
    """
    # Import after mocking
    from index import lambda_handler, RetryableError
    
    # Mock DynamoDB responses
    mock_aws_services['invoices_table'].get_item.return_value = {
        'Item': sample_invoice
    }
    
    mock_aws_services['pos_table'].query.return_value = {
        'Items': [sample_po]
    }
    
    # Mock Bedrock to raise throttling error
    error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
    mock_aws_services['bedrock'].invoke_model.side_effect = ClientError(error_response, 'invoke_model')
    
    # Mock update operations
    mock_aws_services['invoices_table'].update_item.return_value = {}
    mock_aws_services['audit_logs_table'].put_item.return_value = {}
    
    # Execute lambda and expect RetryableError
    event = {'invoice_id': 'inv-12345'}
    
    with pytest.raises(RetryableError) as exc_info:
        lambda_handler(event, None)
    
    assert 'Bedrock API temporarily unavailable' in str(exc_info.value)
    
    # Verify error was logged
    assert mock_aws_services['audit_logs_table'].put_item.called


# Edge Case 4: Bedrock API service unavailable
def test_bedrock_api_service_unavailable(mock_aws_services, sample_invoice, sample_po):
    """
    Test that Bedrock API service unavailable errors are handled as retryable errors.
    
    Expected behavior:
    - Bedrock returns ServiceUnavailable
    - Lambda raises RetryableError
    - Step Functions will retry the operation
    
    Validates: Requirements 5.1, 5.2
    """
    # Import after mocking
    from index import lambda_handler, RetryableError
    
    # Mock DynamoDB responses
    mock_aws_services['invoices_table'].get_item.return_value = {
        'Item': sample_invoice
    }
    
    mock_aws_services['pos_table'].query.return_value = {
        'Items': [sample_po]
    }
    
    # Mock Bedrock to raise service unavailable error
    error_response = {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service temporarily unavailable'}}
    mock_aws_services['bedrock'].invoke_model.side_effect = ClientError(error_response, 'invoke_model')
    
    # Mock update operations
    mock_aws_services['invoices_table'].update_item.return_value = {}
    mock_aws_services['audit_logs_table'].put_item.return_value = {}
    
    # Execute lambda and expect RetryableError
    event = {'invoice_id': 'inv-12345'}
    
    with pytest.raises(RetryableError) as exc_info:
        lambda_handler(event, None)
    
    assert 'Bedrock API temporarily unavailable' in str(exc_info.value)


# Edge Case 5: Bedrock returns malformed JSON
def test_bedrock_returns_malformed_json(mock_aws_services, sample_invoice, sample_po):
    """
    Test that malformed JSON responses from Bedrock are handled gracefully.
    
    Expected behavior:
    - Bedrock returns invalid JSON
    - Lambda handles parsing error
    - Returns fallback match result with no matches
    - Does not crash or raise exception
    
    Validates: Requirements 5.1, 5.2
    """
    # Import after mocking
    from index import lambda_handler
    
    # Mock DynamoDB responses
    mock_aws_services['invoices_table'].get_item.return_value = {
        'Item': sample_invoice
    }
    
    mock_aws_services['pos_table'].query.return_value = {
        'Items': [sample_po]
    }
    
    # Mock Bedrock to return malformed JSON
    mock_aws_services['bedrock'].invoke_model.return_value = {
        'body': MagicMock(read=lambda: json.dumps({
            'content': [{'text': 'This is not valid JSON { broken'}]
        }).encode())
    }
    
    # Mock update operations
    mock_aws_services['invoices_table'].update_item.return_value = {}
    mock_aws_services['audit_logs_table'].put_item.return_value = {}
    
    # Execute lambda
    event = {'invoice_id': 'inv-12345'}
    result = lambda_handler(event, None)
    
    # Assertions - should handle gracefully with fallback
    assert result['statusCode'] == 200
    assert result['matched_po_ids'] == []
    assert result['confidence_score'] == 0


# Edge Case 6: Bedrock returns empty response
def test_bedrock_returns_empty_response(mock_aws_services, sample_invoice, sample_po):
    """
    Test that empty responses from Bedrock are handled as retryable errors.
    
    Expected behavior:
    - Bedrock returns empty content
    - Lambda raises RetryableError (wrapping PermanentError)
    - Step Functions will retry the operation
    
    Validates: Requirements 5.1, 5.2
    """
    # Import after mocking
    from index import lambda_handler, RetryableError
    
    # Mock DynamoDB responses
    mock_aws_services['invoices_table'].get_item.return_value = {
        'Item': sample_invoice
    }
    
    mock_aws_services['pos_table'].query.return_value = {
        'Items': [sample_po]
    }
    
    # Mock Bedrock to return empty content
    mock_aws_services['bedrock'].invoke_model.return_value = {
        'body': MagicMock(read=lambda: json.dumps({
            'content': []
        }).encode())
    }
    
    # Mock update operations
    mock_aws_services['invoices_table'].update_item.return_value = {}
    mock_aws_services['audit_logs_table'].put_item.return_value = {}
    
    # Execute lambda - should raise RetryableError
    event = {'invoice_id': 'inv-12345'}
    
    with pytest.raises(RetryableError) as exc_info:
        lambda_handler(event, None)
    
    assert 'Empty response from Bedrock API' in str(exc_info.value)


# Edge Case 7: Missing invoice_id in event
def test_missing_invoice_id_in_event(mock_aws_services):
    """
    Test that missing invoice_id in event is handled as permanent error.
    
    Expected behavior:
    - Lambda detects missing invoice_id
    - Returns error status
    - Does not attempt to process
    
    Validates: Requirements 5.1, 5.2
    """
    # Import after mocking
    from index import lambda_handler
    
    # Mock update operations
    mock_aws_services['audit_logs_table'].put_item.return_value = {}
    
    # Execute lambda with empty event
    event = {}
    result = lambda_handler(event, None)
    
    # Assertions
    assert result['statusCode'] == 200
    assert result['status'] == 'FLAGGED'
    assert result['flagged_for_manual_review'] is True
    assert 'Missing required field: invoice_id' in result['error']


# Edge Case 8: Invoice not found in DynamoDB
def test_invoice_not_found_in_dynamodb(mock_aws_services):
    """
    Test that missing invoice in DynamoDB is handled as permanent error.
    
    Expected behavior:
    - DynamoDB returns no item
    - Lambda detects missing invoice
    - Returns error status
    
    Validates: Requirements 5.1, 5.2
    """
    # Import after mocking
    from index import lambda_handler
    
    # Mock DynamoDB to return no item
    mock_aws_services['invoices_table'].get_item.return_value = {}
    
    # Mock update operations
    mock_aws_services['audit_logs_table'].put_item.return_value = {}
    
    # Execute lambda
    event = {'invoice_id': 'inv-nonexistent'}
    result = lambda_handler(event, None)
    
    # Assertions
    assert result['statusCode'] == 200
    assert result['status'] == 'FLAGGED'
    assert result['flagged_for_manual_review'] is True
    assert 'Invoice not found' in result['error']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
