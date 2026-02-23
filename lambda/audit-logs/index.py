"""
Audit Logs Lambda Handler
Handles GET /audit-logs endpoint for querying audit trail
"""

import json
import os
import boto3
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
audit_logs_table = dynamodb.Table(os.environ.get('AUDIT_LOGS_TABLE', 'ReconcileAI-AuditLogs'))

def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    """
    Main Lambda handler for audit logs API
    Handles GET /audit-logs with query parameters
    """
    try:
        http_method = event.get('httpMethod', '')
        
        if http_method == 'GET':
            return handle_get_audit_logs(event)
        else:
            return {
                'statusCode': 405,
                'headers': get_cors_headers(),
                'body': json.dumps({'message': 'Method not allowed'})
            }
            
    except Exception as e:
        print(f"Error in audit logs handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'message': 'Internal server error', 'error': str(e)})
        }

def handle_get_audit_logs(event):
    """
    Handle GET /audit-logs request
    Query parameters: entityId, actor, actionType, dateFrom, dateTo
    """
    try:
        # Extract query parameters
        query_params = event.get('queryStringParameters') or {}
        entity_id = query_params.get('entityId', '').strip()
        actor = query_params.get('actor', '').strip()
        action_type = query_params.get('actionType', '').strip()
        date_from = query_params.get('dateFrom', '').strip()
        date_to = query_params.get('dateTo', '').strip()
        
        # Sanitize inputs
        entity_id = sanitize_input(entity_id)
        actor = sanitize_input(actor)
        action_type = sanitize_input(action_type)
        
        logs = []
        
        # Query strategy based on filters
        if entity_id:
            # Use EntityId GSI for efficient querying
            logs = query_by_entity_id(entity_id, date_from, date_to)
        else:
            # Scan with filters (less efficient but necessary for other queries)
            logs = scan_with_filters(actor, action_type, date_from, date_to)
        
        # Sort by timestamp descending (most recent first)
        logs.sort(key=lambda x: x.get('Timestamp', ''), reverse=True)
        
        # Limit results to 1000 for performance
        logs = logs[:1000]
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'logs': logs,
                'count': len(logs)
            }, default=decimal_default)
        }
        
    except Exception as e:
        print(f"Error querying audit logs: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'message': 'Failed to query audit logs', 'error': str(e)})
        }

def query_by_entity_id(entity_id, date_from=None, date_to=None):
    """Query audit logs by entity ID using GSI"""
    try:
        # Use EntityId GSI (EntityId as PK, Timestamp as SK)
        key_condition = Key('EntityId').eq(entity_id)
        
        # Add timestamp range if provided
        if date_from and date_to:
            key_condition = key_condition & Key('Timestamp').between(date_from, date_to)
        elif date_from:
            key_condition = key_condition & Key('Timestamp').gte(date_from)
        elif date_to:
            key_condition = key_condition & Key('Timestamp').lte(date_to)
        
        response = audit_logs_table.query(
            IndexName='EntityIdIndex',
            KeyConditionExpression=key_condition
        )
        
        return response.get('Items', [])
        
    except Exception as e:
        print(f"Error querying by entity ID: {str(e)}")
        return []

def scan_with_filters(actor=None, action_type=None, date_from=None, date_to=None):
    """Scan audit logs with filters"""
    try:
        filter_expression = None
        
        # Build filter expression
        if actor:
            filter_expression = Attr('Actor').eq(actor)
        
        if action_type:
            action_filter = Attr('ActionType').eq(action_type)
            filter_expression = action_filter if not filter_expression else filter_expression & action_filter
        
        if date_from:
            date_from_filter = Attr('Timestamp').gte(date_from)
            filter_expression = date_from_filter if not filter_expression else filter_expression & date_from_filter
        
        if date_to:
            date_to_filter = Attr('Timestamp').lte(date_to)
            filter_expression = date_to_filter if not filter_expression else filter_expression & date_to_filter
        
        # Perform scan
        if filter_expression:
            response = audit_logs_table.scan(
                FilterExpression=filter_expression,
                Limit=1000  # Limit scan results for performance
            )
        else:
            # No filters - return recent logs
            response = audit_logs_table.scan(Limit=1000)
        
        return response.get('Items', [])
        
    except Exception as e:
        print(f"Error scanning audit logs: {str(e)}")
        return []

def sanitize_input(value):
    """
    Sanitize user input to prevent injection attacks
    Removes dangerous characters and patterns
    """
    if not value:
        return value
    
    # Remove control characters
    sanitized = ''.join(char for char in value if ord(char) >= 32 and ord(char) != 127)
    
    # Remove dangerous patterns (case-insensitive)
    dangerous_patterns = [
        '<script', '</script>', 'javascript:', 'onerror=', 'onload=',
        'onclick=', 'onmouseover=', '<iframe', '</iframe>', 'vbscript:',
        'onabort=', 'onblur=', 'onchange=', 'onfocus=', 'onreset=',
        'onselect=', 'onsubmit='
    ]
    
    sanitized_lower = sanitized.lower()
    for pattern in dangerous_patterns:
        if pattern in sanitized_lower:
            sanitized = sanitized.replace(pattern, '')
            sanitized = sanitized.replace(pattern.upper(), '')
            sanitized = sanitized.replace(pattern.capitalize(), '')
    
    # Escape HTML special characters
    sanitized = sanitized.replace('<', '&lt;')
    sanitized = sanitized.replace('>', '&gt;')
    sanitized = sanitized.replace('"', '&quot;')
    sanitized = sanitized.replace("'", '&#x27;')
    
    return sanitized.strip()

def get_cors_headers():
    """Return CORS headers for API responses"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',  # Configure with specific domain in production
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,OPTIONS'
    }
