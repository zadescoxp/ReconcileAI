"""
PO Management Lambda Handler
Handles POST /pos (upload PO) and GET /pos (search POs)
"""

import json
import os
import uuid
import re
import base64
from datetime import datetime
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key, Attr

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
lambda_client = boto3.client('lambda')
pos_table = dynamodb.Table(os.environ['POS_TABLE_NAME'])
audit_logs_table = dynamodb.Table(os.environ['AUDIT_LOGS_TABLE_NAME'])
pdf_extraction_lambda = os.environ.get('PDF_EXTRACTION_LAMBDA_NAME', 'ReconcileAI-PDFExtraction')
invoice_bucket = os.environ.get('INVOICE_BUCKET_NAME')


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


def handle_parse_pdf(event):
    """Handle POST /pos/parse-pdf - Parse PDF file to extract PO data"""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        file_content = body.get('fileContent')
        file_name = body.get('fileName', 'document.pdf')
        
        if not file_content:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'fileContent is required'
                })
            }
        
        # Decode base64 PDF
        pdf_bytes = base64.b64decode(file_content)
        
        # Extract text directly using pdfplumber
        import io
        import pdfplumber
        
        pdf_file = io.BytesIO(pdf_bytes)
        extracted_text = ""
        
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
        
        if not extracted_text or len(extracted_text.strip()) < 10:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Could not extract text from PDF'
                })
            }
        
        # Parse PO metadata from text
        metadata = parse_po_from_text(extracted_text)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'metadata': metadata
            }, default=str)
        }
        
    except Exception as e:
        print(f"Error in handle_parse_pdf: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Failed to parse PDF: {str(e)}'
            })
        }


def parse_po_from_text(text):
    """Parse PO metadata from extracted text"""
    metadata = {
        'vendorName': '',
        'poNumber': '',
        'totalAmount': 0,
        'lineItems': []
    }
    
    lines = text.split('\n')
    
    # Parse PO number - more flexible patterns
    po_number_patterns = [
        r'(?:PO|Purchase\s+Order)\s*(?:Number|#|No\.?)?\s*:?\s*([A-Z0-9\-]+)',
        r'Order\s*(?:Number|#|No\.?)?\s*:?\s*([A-Z0-9\-]+)',
    ]
    for pattern in po_number_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            metadata['poNumber'] = match.group(1).strip()
            break
    
    # Parse vendor name - look in first 10 lines
    vendor_patterns = [
        r'(?:Vendor|Supplier|From)\s*:?\s*([A-Za-z0-9\s&\.,\-\']+)',
        r'^([A-Z][A-Za-z\s&\.,\-\']{5,50})$',  # Company name pattern
    ]
    for i, line in enumerate(lines[:10]):
        for pattern in vendor_patterns:
            match = re.search(pattern, line, re.IGNORECASE if 'Vendor' in pattern else 0)
            if match:
                vendor_name = match.group(1).strip()
                vendor_name = re.sub(r'\s+', ' ', vendor_name)
                # Validate it's not a header
                if len(vendor_name) > 3 and not any(x in vendor_name.lower() for x in ['purchase', 'order', 'date', 'number']):
                    metadata['vendorName'] = vendor_name
                    break
        if metadata['vendorName']:
            break
    
    # Parse total amount
    total_patterns = [
        r'(?:Total\s+Authorized\s+Amount|Grand\s+Total|Total\s+Amount|Total)\s*:?\s*\$?\s*([\d,]+\.?\d{0,2})',
    ]
    for pattern in total_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                metadata['totalAmount'] = float(amount_str)
                break
            except ValueError:
                continue
    
    # Parse line items - look for table structure
    line_number = 1
    header_idx = -1
    
    # Find table header
    for i, line in enumerate(lines):
        if re.search(r'(?:Item|Description|Product).*(?:Qty|Quantity).*(?:Price|Unit|Rate)', line, re.IGNORECASE):
            header_idx = i
            break
    
    if header_idx >= 0:
        # Parse rows after header
        for i in range(header_idx + 1, min(header_idx + 50, len(lines))):
            line = lines[i].strip()
            if not line or len(line) < 5:
                continue
            
            # Stop at footer
            if re.search(r'(?:subtotal|tax|total|notes|terms)', line, re.IGNORECASE):
                break
            
            # Extract numbers from line
            parts = line.split()
            numbers = []
            desc_parts = []
            
            for part in parts:
                num_match = re.match(r'\$?([\d,]+\.?\d{0,2})$', part)
                if num_match:
                    try:
                        numbers.append(float(num_match.group(1).replace(',', '')))
                    except:
                        desc_parts.append(part)
                else:
                    desc_parts.append(part)
            
            # Need description and at least 2 numbers (qty, price)
            if len(desc_parts) >= 1 and len(numbers) >= 2:
                description = ' '.join(desc_parts)
                
                if len(numbers) >= 3:
                    quantity = numbers[0]
                    unit_price = numbers[1]
                    total_price = numbers[2]
                else:
                    quantity = numbers[0]
                    unit_price = numbers[1]
                    total_price = quantity * unit_price
                
                if quantity > 0 and unit_price > 0:
                    metadata['lineItems'].append({
                        'LineNumber': line_number,
                        'ItemDescription': description[:100],
                        'Quantity': quantity,
                        'UnitPrice': unit_price,
                        'TotalPrice': total_price
                    })
                    line_number += 1
    
    # Calculate total if not found
    if metadata['totalAmount'] == 0 and metadata['lineItems']:
        metadata['totalAmount'] = sum(item['TotalPrice'] for item in metadata['lineItems'])
    
    # Set defaults if not found
    if not metadata['vendorName']:
        metadata['vendorName'] = 'Unknown Vendor'
    if not metadata['poNumber']:
        metadata['poNumber'] = f'PO-{uuid.uuid4().hex[:8].upper()}'
    
    return metadata


def lambda_handler(event, context):
    """Main Lambda handler for PO management"""
    print(f"Event: {json.dumps(event)}")
    
    http_method = event.get('httpMethod')
    path = event.get('path', '')
    
    # Handle PDF parsing endpoint
    if http_method == 'POST' and '/parse-pdf' in path:
        return handle_parse_pdf(event)
    elif http_method == 'POST':
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
