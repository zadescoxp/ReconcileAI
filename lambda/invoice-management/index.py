"""
Invoice Management Lambda Handler
Handles GET /invoices, POST /invoices/{id}/approve, POST /invoices/{id}/reject
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
sfn_client = boto3.client('stepfunctions')

invoices_table = dynamodb.Table(os.environ['INVOICES_TABLE_NAME'])
audit_logs_table = dynamodb.Table(os.environ['AUDIT_LOGS_TABLE_NAME'])
state_machine_arn = os.environ['STATE_MACHINE_ARN']


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
                'EntityType': 'Invoice',
                'EntityId': entity_id,
                'Details': details
            }
        )
    except Exception as e:
        print(f"Error logging audit: {str(e)}")


def handle_get_invoices(event):
    """Handle GET /invoices - Query invoices with filters"""
    try:
        # Get query parameters
        query_params = event.get('queryStringParameters') or {}
        
        # Sanitize query parameters
        status = sanitize_input(query_params.get('status'))
        vendor_name = sanitize_input(query_params.get('vendorName'))
        date_from = sanitize_input(query_params.get('dateFrom'))
        date_to = sanitize_input(query_params.get('dateTo'))
        
        invoices = []
        
        # If filtering by status, use StatusIndex GSI
        if status:
            response = invoices_table.query(
                IndexName='StatusIndex',
                KeyConditionExpression=Key('Status').eq(status)
            )
            invoices = response.get('Items', [])
        # If filtering by vendor name, use VendorNameIndex GSI
        elif vendor_name:
            response = invoices_table.query(
                IndexName='VendorNameIndex',
                KeyConditionExpression=Key('VendorName').eq(vendor_name)
            )
            invoices = response.get('Items', [])
        else:
            # Scan table (less efficient, but necessary for other queries)
            response = invoices_table.scan()
            invoices = response.get('Items', [])
        
        # Apply additional filters
        if vendor_name and status:
            # If both filters, need to filter after query
            invoices = [inv for inv in invoices if inv.get('VendorName') == vendor_name]
        
        # Filter by date range
        if date_from or date_to:
            invoices = [
                inv for inv in invoices
                if (not date_from or inv.get('ReceivedDate', '') >= date_from) and
                   (not date_to or inv.get('ReceivedDate', '') <= date_to)
            ]
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'invoices': invoices,
                'count': len(invoices)
            }, default=str)
        }
        
    except Exception as e:
        print(f"Error in handle_get_invoices: {str(e)}")
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


def handle_approve_invoice(event):
    """Handle POST /invoices/{id}/approve - Approve invoice"""
    try:
        # Get invoice ID from path parameters
        invoice_id = event.get('pathParameters', {}).get('id')
        if not invoice_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Invoice ID is required'
                })
            }
        
        # Sanitize invoice ID
        invoice_id = sanitize_input(invoice_id)
        
        # Parse request body for optional comment
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError:
                pass
        
        comment = sanitize_input(body.get('comment', ''))
        
        # Get user from Cognito claims
        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
        approver_id = claims.get('sub', 'unknown')
        approver_email = claims.get('email', 'unknown')
        
        # Get invoice from DynamoDB
        response = invoices_table.get_item(Key={'InvoiceId': invoice_id})
        invoice = response.get('Item')
        
        if not invoice:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Invoice not found'
                })
            }
        
        # Update invoice status to Approved
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        invoices_table.update_item(
            Key={'InvoiceId': invoice_id},
            UpdateExpression='SET #status = :status, ApprovedBy = :approver, ApprovedAt = :timestamp, ApprovalComment = :comment',
            ExpressionAttributeNames={
                '#status': 'Status'
            },
            ExpressionAttributeValues={
                ':status': 'Approved',
                ':approver': approver_id,
                ':timestamp': timestamp,
                ':comment': comment
            }
        )
        
        # Log approval to audit trail
        log_audit(
            actor=approver_id,
            action_type='InvoiceApproved',
            entity_id=invoice_id,
            details={
                'invoiceNumber': invoice.get('InvoiceNumber'),
                'vendorName': invoice.get('VendorName'),
                'approverEmail': approver_email,
                'comment': comment,
                'timestamp': timestamp
            }
        )
        
        # Resume Step Function execution if StepFunctionArn exists
        step_function_arn = invoice.get('StepFunctionArn')
        if step_function_arn:
            try:
                # Note: For paused executions, we would use SendTaskSuccess
                # For now, we just update the status
                print(f"Invoice approved, Step Function ARN: {step_function_arn}")
            except Exception as e:
                print(f"Error resuming Step Function: {str(e)}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Invoice approved successfully',
                'invoiceId': invoice_id,
                'status': 'Approved',
                'approvedBy': approver_id,
                'approvedAt': timestamp
            })
        }
        
    except Exception as e:
        print(f"Error in handle_approve_invoice: {str(e)}")
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


def handle_reject_invoice(event):
    """Handle POST /invoices/{id}/reject - Reject invoice"""
    try:
        # Get invoice ID from path parameters
        invoice_id = event.get('pathParameters', {}).get('id')
        if not invoice_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Invoice ID is required'
                })
            }
        
        # Sanitize invoice ID
        invoice_id = sanitize_input(invoice_id)
        
        # Parse request body for required reason
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
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
        
        reason = sanitize_input(body.get('reason', ''))
        if not reason:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Rejection reason is required'
                })
            }
        
        # Get user from Cognito claims
        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
        rejector_id = claims.get('sub', 'unknown')
        rejector_email = claims.get('email', 'unknown')
        
        # Get invoice from DynamoDB
        response = invoices_table.get_item(Key={'InvoiceId': invoice_id})
        invoice = response.get('Item')
        
        if not invoice:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Invoice not found'
                })
            }
        
        # Update invoice status to Rejected
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        invoices_table.update_item(
            Key={'InvoiceId': invoice_id},
            UpdateExpression='SET #status = :status, RejectedBy = :rejector, RejectedAt = :timestamp, RejectionReason = :reason',
            ExpressionAttributeNames={
                '#status': 'Status'
            },
            ExpressionAttributeValues={
                ':status': 'Rejected',
                ':rejector': rejector_id,
                ':timestamp': timestamp,
                ':reason': reason
            }
        )
        
        # Log rejection to audit trail
        log_audit(
            actor=rejector_id,
            action_type='InvoiceRejected',
            entity_id=invoice_id,
            details={
                'invoiceNumber': invoice.get('InvoiceNumber'),
                'vendorName': invoice.get('VendorName'),
                'rejectorEmail': rejector_email,
                'reason': reason,
                'timestamp': timestamp
            }
        )
        
        # Halt Step Function execution if StepFunctionArn exists
        step_function_arn = invoice.get('StepFunctionArn')
        if step_function_arn:
            try:
                # Note: For paused executions, we would use SendTaskFailure
                # For now, we just update the status
                print(f"Invoice rejected, Step Function ARN: {step_function_arn}")
            except Exception as e:
                print(f"Error halting Step Function: {str(e)}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Invoice rejected successfully',
                'invoiceId': invoice_id,
                'status': 'Rejected',
                'rejectedBy': rejector_id,
                'rejectedAt': timestamp,
                'reason': reason
            })
        }
        
    except Exception as e:
        print(f"Error in handle_reject_invoice: {str(e)}")
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
    """Main Lambda handler for invoice management"""
    print(f"Event: {json.dumps(event)}")
    
    http_method = event.get('httpMethod')
    path = event.get('path', '')
    
    # Route based on HTTP method and path
    if http_method == 'GET' and path == '/invoices':
        return handle_get_invoices(event)
    elif http_method == 'POST' and '/approve' in path:
        return handle_approve_invoice(event)
    elif http_method == 'POST' and '/reject' in path:
        return handle_reject_invoice(event)
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
