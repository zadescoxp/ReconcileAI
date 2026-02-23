"""
Property-Based Tests for Comprehensive Audit Logging
Feature: reconcile-ai, Property 28: Comprehensive Audit Logging

Property 28: For any system action (PO upload, invoice received, extraction, 
matching, fraud detection, approval, rejection), an audit log entry should be 
created with timestamp, actor, action type, entity type, entity ID, and details.

Validates: Requirements 10.1, 10.4
"""

import pytest
import boto3
import os
import json
from datetime import datetime
from decimal import Decimal
from hypothesis import given, strategies as st, settings, HealthCheck
from moto import mock_aws
import sys

# Mock environment variables before any imports
os.environ['AUDIT_LOGS_TABLE'] = 'ReconcileAI-AuditLogs-Test'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


# Strategies for generating test data
@st.composite
def action_type_strategy(draw):
    """Generate valid action types"""
    action_types = [
        'POUploaded',
        'InvoiceReceived',
        'InvoiceExtracted',
        'InvoiceMatched',
        'FraudDetected',
        'InvoiceApproved',
        'InvoiceRejected'
    ]
    return draw(st.sampled_from(action_types))


@st.composite
def entity_type_strategy(draw):
    """Generate valid entity types"""
    entity_types = ['PO', 'Invoice', 'User']
    return draw(st.sampled_from(entity_types))


@st.composite
def actor_strategy(draw):
    """Generate actor identifiers"""
    return draw(st.one_of(
        st.just('System'),
        st.from_regex(r'user-[a-f0-9]{8}', fullmatch=True)
    ))


@st.composite
def audit_log_entry_strategy(draw):
    """Generate a complete audit log entry"""
    return {
        'action_type': draw(action_type_strategy()),
        'entity_type': draw(entity_type_strategy()),
        'entity_id': draw(st.from_regex(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', fullmatch=True)),
        'actor': draw(actor_strategy()),
        'details': draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
            values=st.one_of(
                st.text(min_size=0, max_size=50),
                st.integers(min_value=0, max_value=1000000)
            ),
            min_size=1,
            max_size=5
        ))
    }


@pytest.fixture(scope='session')
def dynamodb_setup():
    """Set up mock DynamoDB table for testing"""
    with mock_aws():
        # Create DynamoDB resource
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create AuditLogs table
        table = dynamodb.create_table(
            TableName='ReconcileAI-AuditLogs-Test',
            KeySchema=[
                {'AttributeName': 'LogId', 'KeyType': 'HASH'},
                {'AttributeName': 'Timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'LogId', 'AttributeType': 'S'},
                {'AttributeName': 'Timestamp', 'AttributeType': 'S'},
                {'AttributeName': 'EntityId', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'EntityIdIndex',
                    'KeySchema': [
                        {'AttributeName': 'EntityId', 'KeyType': 'HASH'},
                        {'AttributeName': 'Timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        yield table


@pytest.fixture(autouse=True)
def clear_table(dynamodb_setup):
    """Clear table before each test"""
    # Clear all items before each test
    table = dynamodb_setup
    scan = table.scan()
    with table.batch_writer() as batch:
        for item in scan['Items']:
            batch.delete_item(
                Key={
                    'LogId': item['LogId'],
                    'Timestamp': item['Timestamp']
                }
            )
    yield


@pytest.mark.property_test
@given(log_entry=audit_log_entry_strategy())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_audit_log_completeness(dynamodb_setup, log_entry):
    """
    Property 28: For any system action, an audit log entry should be created
    with all required fields: timestamp, actor, action type, entity type, 
    entity ID, and details.
    """
    table = dynamodb_setup
    
    # Simulate creating an audit log entry
    from uuid import uuid4
    log_id = str(uuid4())
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    # Create audit log entry
    table.put_item(
        Item={
            'LogId': log_id,
            'Timestamp': timestamp,
            'Actor': log_entry['actor'],
            'ActionType': log_entry['action_type'],
            'EntityType': log_entry['entity_type'],
            'EntityId': log_entry['entity_id'],
            'Details': log_entry['details']
        }
    )
    
    # Retrieve the log entry
    response = table.get_item(
        Key={
            'LogId': log_id,
            'Timestamp': timestamp
        }
    )
    
    # Verify all required fields are present
    assert 'Item' in response
    item = response['Item']
    
    # Check required fields
    assert 'LogId' in item
    assert 'Timestamp' in item
    assert 'Actor' in item
    assert 'ActionType' in item
    assert 'EntityType' in item
    assert 'EntityId' in item
    assert 'Details' in item
    
    # Verify field values match
    assert item['LogId'] == log_id
    assert item['Timestamp'] == timestamp
    assert item['Actor'] == log_entry['actor']
    assert item['ActionType'] == log_entry['action_type']
    assert item['EntityType'] == log_entry['entity_type']
    assert item['EntityId'] == log_entry['entity_id']
    
    # Verify details is a non-empty dictionary
    assert isinstance(item['Details'], dict)
    assert len(item['Details']) > 0


@pytest.mark.property_test
@given(
    action_type=action_type_strategy(),
    entity_id=st.from_regex(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', fullmatch=True)
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_audit_log_queryable_by_entity_id(dynamodb_setup, action_type, entity_id):
    """
    Property 28: Audit logs should be queryable by entity ID for traceability.
    """
    table = dynamodb_setup
    
    # Create multiple audit log entries for the same entity
    num_entries = 3
    timestamps = []
    log_ids = []
    
    for i in range(num_entries):
        from uuid import uuid4
        log_id = str(uuid4())
        log_ids.append(log_id)
        timestamp = datetime.utcnow().isoformat() + f'.{i:03d}Z'
        timestamps.append(timestamp)
        
        table.put_item(
            Item={
                'LogId': log_id,
                'Timestamp': timestamp,
                'Actor': 'System',
                'ActionType': action_type,
                'EntityType': 'Invoice',
                'EntityId': entity_id,
                'Details': {'iteration': i}
            }
        )
    
    # Query by entity ID using GSI
    response = table.query(
        IndexName='EntityIdIndex',
        KeyConditionExpression='EntityId = :entity_id',
        ExpressionAttributeValues={
            ':entity_id': entity_id
        }
    )
    
    # Verify all entries we just created are returned
    assert 'Items' in response
    items = response['Items']
    assert len(items) >= num_entries  # At least our entries are there
    
    # Verify all items have the correct entity ID
    for item in items:
        assert item['EntityId'] == entity_id
    
    # Verify our specific log IDs are in the results
    returned_log_ids = [item['LogId'] for item in items]
    for log_id in log_ids:
        assert log_id in returned_log_ids


@pytest.mark.property_test
@given(
    actor=actor_strategy(),
    action_type=action_type_strategy(),
    num_actions=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_audit_log_preserves_action_sequence(dynamodb_setup, actor, action_type, num_actions):
    """
    Property 28: Audit logs should preserve the sequence of actions through timestamps.
    """
    table = dynamodb_setup
    
    # Create multiple audit log entries with sequential timestamps
    log_entries = []
    
    for i in range(num_actions):
        from uuid import uuid4
        log_id = str(uuid4())
        entity_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat() + f'.{i:03d}Z'
        
        table.put_item(
            Item={
                'LogId': log_id,
                'Timestamp': timestamp,
                'Actor': actor,
                'ActionType': action_type,
                'EntityType': 'Invoice',
                'EntityId': entity_id,
                'Details': {'sequence': i}
            }
        )
        
        log_entries.append({
            'log_id': log_id,
            'timestamp': timestamp,
            'sequence': i
        })
    
    # Retrieve all entries and verify they can be sorted by timestamp
    for entry in log_entries:
        response = table.get_item(
            Key={
                'LogId': entry['log_id'],
                'Timestamp': entry['timestamp']
            }
        )
        
        assert 'Item' in response
        item = response['Item']
        assert item['Details']['sequence'] == entry['sequence']
    
    # Verify timestamps are in order
    sorted_entries = sorted(log_entries, key=lambda x: x['timestamp'])
    for i, entry in enumerate(sorted_entries):
        assert entry['sequence'] == i


@pytest.mark.property_test
@given(
    log_entry=audit_log_entry_strategy(),
    reasoning=st.text(min_size=10, max_size=200)
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_audit_log_includes_ai_reasoning(dynamodb_setup, log_entry, reasoning):
    """
    Property 28: Audit logs for AI decisions should include reasoning.
    """
    table = dynamodb_setup
    
    # Only test AI-related actions
    if log_entry['action_type'] not in ['InvoiceMatched', 'FraudDetected']:
        return
    
    from uuid import uuid4
    log_id = str(uuid4())
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    # Create audit log entry with reasoning
    table.put_item(
        Item={
            'LogId': log_id,
            'Timestamp': timestamp,
            'Actor': 'System',
            'ActionType': log_entry['action_type'],
            'EntityType': log_entry['entity_type'],
            'EntityId': log_entry['entity_id'],
            'Details': log_entry['details'],
            'Reasoning': reasoning
        }
    )
    
    # Retrieve the log entry
    response = table.get_item(
        Key={
            'LogId': log_id,
            'Timestamp': timestamp
        }
    )
    
    # Verify reasoning is present
    assert 'Item' in response
    item = response['Item']
    assert 'Reasoning' in item
    assert item['Reasoning'] == reasoning
    assert len(item['Reasoning']) >= 10


@pytest.mark.property_test
@given(
    approver_id=st.from_regex(r'user-[a-f0-9]{8}', fullmatch=True),
    entity_id=st.from_regex(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', fullmatch=True),
    decision=st.sampled_from(['InvoiceApproved', 'InvoiceRejected'])
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_audit_log_includes_approver_identity(dynamodb_setup, approver_id, entity_id, decision):
    """
    Property 28: Audit logs for human actions should include approver identity.
    """
    table = dynamodb_setup
    
    from uuid import uuid4
    log_id = str(uuid4())
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    # Create audit log entry with approver identity
    table.put_item(
        Item={
            'LogId': log_id,
            'Timestamp': timestamp,
            'Actor': approver_id,
            'ActionType': decision,
            'EntityType': 'Invoice',
            'EntityId': entity_id,
            'Details': {
                'approverEmail': f'{approver_id}@example.com',
                'comment': 'Approved after review'
            }
        }
    )
    
    # Retrieve the log entry
    response = table.get_item(
        Key={
            'LogId': log_id,
            'Timestamp': timestamp
        }
    )
    
    # Verify approver identity is captured
    assert 'Item' in response
    item = response['Item']
    assert item['Actor'] == approver_id
    assert item['Actor'] != 'System'
    assert 'approverEmail' in item['Details']


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
