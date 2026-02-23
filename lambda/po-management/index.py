"""
PO Management Lambda Handler
Handles POST /pos (upload PO) and GET /pos (search POs)
"""

import json
import os
import uuid
import re
from datetime import datetime
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key, Attr

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
pos_table = dynamodb.Table(os.environ['POS_TABLE_NAME'])
audit_logs_table = dynamodb.Table(os.environ['AUDIT_LOGS_TABLE_NAME'])


def sanitize_input(value):
    """
    Sanitize user input to prevent injection attacks.
    Removes or escapes special characters.
    """
    if value is None:
        return None
    
    if isinstance(value, str):
        # Remove control characters and potential injection patterns
        value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
        
        # Remove dangerous JavaScript patterns (case-insensitive)
        dangerous_patterns = [
            r'javascript:',
            r'data:text/html',
            r'vbscript:',
            r'on\w+\s*=',  # Event handlers like onclick=, onerror=, onload=
        ]
        for pattern in dangerous_patterns:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        # Escape common injection characters
        value = value.replace('<', '&lt;').replace('>', '&gt;')
        value = value.replace('"', '&quot;').replace("'", '&#39;')
        return value.strip()
    
    return value


def validate_po(po_data):
    """
    Validate PO has all required fields.
    Returns (is_valid, error_message)
    """
    required_fields = ['vendorName', 'poNumber', 'lineItems']
    
    for field in required_fields:
        if field not in po_data or not po_data[field]:
            return False, f"Missing required field: {field}"
    
    # Validate line items
    line_items = po_data.get('lineItems', [])
    if not isinstance(line_items, list) or len(line_items) == 0:
        return False, "lineItems must be a non-empty array"
    
    for idx, item in enumerate(line_items):
        required_item_fields = ['itemDescription', 'quantity', 'unitPrice']
        for field in required_item_fields:
            if field not in item or item[field] is None:
                return False, f"Line item {idx + 1} missing required field: {field}"
        
        # Validate numeric fields
        try:
            quantity = int(item['quantity'])
            if quantity <= 0:
                return False, f"Line item {idx + 1} quantity must be positive"
        except (ValueError, TypeError):
            return False, f"Line item {idx + 1} quantity must be a valid number"
        
        try:
            unit_price = float(item['unitPrice'])
            if unit_price < 0:
                return False, f"Line item {idx + 1} unitPrice must be non-negative"
        except (ValueError, TypeError):
            return False, f"Line item {idx + 1} unitPrice must be a valid number"
    
    return True, None


def sanitize_po_data(po_data):
    """Sanitize all string fields in PO data"""
    sanitized = {}
    
    for key, value in po_data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_input(value)
        elif isinstance(value, list):
            sanitized[key] = [sanitize_line_item(item) for item in value]
        else:
            sanitized[key] = value
    
    return sanitized


def sanitize_line_item(item):
    """Sanitize line item fields"""
    sanitized = {}
    for key, value in item.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_input(value)
        else:
            sanitized[key] = value
    return sanitized


def calculate_total_amount(line_items):
    """Calculate total amount from line items"""
    total = Decimal('0')
    for item in line_items:
        quantity = Decimal(str(item['quantity']))
        unit_price = Decimal(str(item['unitPrice']))
        total += quantity * unit_price
    return total


def log_audit(actor, action_type, entity_id, details):
    """Log action to audit trail"""
    try:
        log_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        audit_logs_table.put_item(
            Item={
                'LogId': log_id,
                'Timestamp': timestamp,
                'Actor': actor,
                'ActionType': action_type,
                'EntityType': 'PO',
                'EntityId': entity_id,
                'Details': details
            }
        )
    except Exception as e:
        print(f"Error logging audit: {str(e)}")


def handle_post_po(event):
    """Handle POST /pos - Upload PO"""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Sanitize input
        body = sanitize_po_data(body)
        
        # Validate PO
        is_valid, error_message = validate_po(body)
        if not is_valid:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': error_message
                })
            }
        
        # Generate PO ID
        po_id = str(uuid.uuid4())
        
        # Calculate total amount
        total_amount = calculate_total_amount(body['lineItems'])
        
        # Get user from Cognito claims
        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
        uploaded_by = claims.get('sub', 'unknown')
        
        # Prepare line items with calculated totals
        line_items = []
        for idx, item in enumerate(body['lineItems']):
            quantity = Decimal(str(item['quantity']))
            unit_price = Decimal(str(item['unitPrice']))
            total_price = quantity * unit_price
            
            line_items.append({
                'LineNumber': idx + 1,
                'ItemDescription': item['itemDescription'],
                'Quantity': int(quantity),
                'UnitPrice': float(unit_price),
                'TotalPrice': float(total_price),
                'MatchedQuantity': 0
            })
        
        # Store PO in DynamoDB
        upload_date = datetime.utcnow().isoformat() + 'Z'
        
        po_item = {
            'POId': po_id,
            'VendorName': body['vendorName'],
            'PONumber': body['poNumber'],
            'LineItems': line_items,
            'TotalAmount': float(total_amount),
            'UploadDate': upload_date,
            'UploadedBy': uploaded_by,
            'Status': 'Active'
        }
        
        pos_table.put_item(Item=po_item)
        
        # Log to audit trail
        log_audit(
            actor=uploaded_by,
            action_type='POUploaded',
            entity_id=po_id,
            details={
                'poNumber': body['poNumber'],
                'vendorName': body['vendorName'],
                'totalAmount': float(total_amount),
                'lineItemCount': len(line_items)
            }
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'PO uploaded successfully',
                'poId': po_id,
                'po': po_item
            }, default=str)
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Invalid JSON in request body'
            })
        }
    except Exception as e:
        print(f"Error in handle_post_po: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error'
            })
        }


def handle_get_pos(event):
    """Handle GET /pos - Search and retrieve POs"""
    try:
        # Get query parameters
        query_params = event.get('queryStringParameters') or {}
        
        # Sanitize query parameters
        po_number = sanitize_input(query_params.get('poNumber'))
        vendor_name = sanitize_input(query_params.get('vendorName'))
        date_from = sanitize_input(query_params.get('dateFrom'))
        date_to = sanitize_input(query_params.get('dateTo'))
        
        # If searching by vendor name, use GSI
        if vendor_name:
            response = pos_table.query(
                IndexName='VendorNameIndex',
                KeyConditionExpression=Key('VendorName').eq(vendor_name)
            )
            pos = response.get('Items', [])
            
            # Filter by date range if provided
            if date_from or date_to:
                pos = [
                    po for po in pos
                    if (not date_from or po.get('UploadDate', '') >= date_from) and
                       (not date_to or po.get('UploadDate', '') <= date_to)
                ]
        else:
            # Scan table (less efficient, but necessary for other queries)
            response = pos_table.scan()
            pos = response.get('Items', [])
        
        # Filter by PO number if provided
        if po_number:
            pos = [po for po in pos if po.get('PONumber') == po_number]
        
        # Filter by date range if not already filtered
        if not vendor_name and (date_from or date_to):
            pos = [
                po for po in pos
                if (not date_from or po.get('UploadDate', '') >= date_from) and
                   (not date_to or po.get('UploadDate', '') <= date_to)
            ]
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'pos': pos,
                'count': len(pos)
            }, default=str)
        }
        
    except Exception as e:
        print(f"Error in handle_get_pos: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error'
            })
        }


def lambda_handler(event, context):
    """Main Lambda handler for PO management"""
    print(f"Event: {json.dumps(event)}")
    
    http_method = event.get('httpMethod')
    
    if http_method == 'POST':
        return handle_post_po(event)
    elif http_method == 'GET':
        return handle_get_pos(event)
    else:
        return {
            'statusCode': 405,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Method not allowed'
            })
        }
