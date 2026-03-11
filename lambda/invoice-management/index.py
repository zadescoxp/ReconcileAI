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


def handle_get_invoice_by_id(event):
    """Handle GET /invoices/{id} - Get invoice details with matched POs and audit trail"""
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
        
        # Get matched POs if any
        matched_pos = []
        if invoice.get('MatchedPOIds'):
            pos_table = dynamodb.Table(os.environ.get('POS_TABLE_NAME', 'ReconcileAI-POs'))
            for po_id in invoice['MatchedPOIds']:
                try:
                    po_response = pos_table.get_item(Key={'POId': po_id})
                    if po_response.get('Item'):
                        matched_pos.append(po_response['Item'])
                except Exception as e:
                    print(f"Error fetching PO {po_id}: {str(e)}")
        
        # Get audit trail for this invoice
        audit_trail = []
        try:
            audit_response = audit_logs_table.query(
                IndexName='EntityIdIndex',
                KeyConditionExpression=Key('EntityId').eq(invoice_id),
                ScanIndexForward=False  # Most recent first
            )
            audit_trail = audit_response.get('Items', [])
        except Exception as e:
            print(f"Error fetching audit trail: {str(e)}")
            # Continue without audit trail if index doesn't exist
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'invoice': invoice,
                'matchedPOs': matched_pos,
                'auditTrail': audit_trail
            }, default=str)
        }
        
    except Exception as e:
        print(f"Error in handle_get_invoice_by_id: {str(e)}")
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


def handle_create_invoice(event):
    """Handle POST /invoices - Create new invoice from uploaded data"""
    try:
        # Parse request body
        if not event.get('body'):
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Request body is required'
                })
            }
        
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
        
        # Validate required fields
        vendor_name = sanitize_input(body.get('vendorName'))
        invoice_number = sanitize_input(body.get('invoiceNumber'))
        line_items = body.get('lineItems', [])
        uploaded_by = sanitize_input(body.get('uploadedBy', 'unknown'))
        
        if not vendor_name or not invoice_number:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'vendorName and invoiceNumber are required'
                })
            }
        
        if not line_items or len(line_items) == 0:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'At least one line item is required'
                })
            }
        
        # Generate invoice ID
        invoice_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        # Calculate total amount
        total_amount = Decimal('0')
        for item in line_items:
            total_amount += Decimal(str(item.get('TotalPrice', 0)))
        
        # Create invoice record
        invoice = {
            'InvoiceId': invoice_id,
            'VendorName': vendor_name,
            'InvoiceNumber': invoice_number,
            'InvoiceDate': timestamp,
            'LineItems': line_items,
            'TotalAmount': total_amount,
            'Status': 'Received',
            'MatchedPOIds': [],
            'Discrepancies': [],
            'FraudFlags': [],
            'AIReasoning': '',
            'ReceivedDate': timestamp,
            'S3Key': f'invoices/{invoice_id}.json',
            'UploadedBy': uploaded_by
        }
        
        # Save to DynamoDB
        invoices_table.put_item(Item=invoice)
        
        # Log to audit trail
        log_audit(
            actor=uploaded_by,
            action_type='InvoiceCreated',
            entity_id=invoice_id,
            details={
                'invoiceNumber': invoice_number,
                'vendorName': vendor_name,
                'totalAmount': str(total_amount),
                'lineItemCount': len(line_items),
                'timestamp': timestamp
            }
        )
        
        # Trigger Step Function for processing
        try:
            sfn_response = sfn_client.start_execution(
                stateMachineArn=state_machine_arn,
                name=f"invoice-{invoice_id}",
                input=json.dumps({
                    'invoiceId': invoice_id,
                    's3Key': invoice['S3Key']
                })
            )
            
            # Update invoice with Step Function ARN
            invoices_table.update_item(
                Key={'InvoiceId': invoice_id},
                UpdateExpression='SET StepFunctionArn = :arn',
                ExpressionAttributeValues={
                    ':arn': sfn_response['executionArn']
                }
            )
        except Exception as e:
            print(f"Error starting Step Function: {str(e)}")
            # Continue even if Step Function fails
        
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Invoice created successfully',
                'invoiceId': invoice_id,
                'status': 'Received'
            })
        }
        
    except Exception as e:
        print(f"Error in handle_create_invoice: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
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
    elif http_method == 'GET' and path.startswith('/invoices/') and not ('approve' in path or 'reject' in path):
        return handle_get_invoice_by_id(event)
    elif http_method == 'POST' and path == '/invoices':
        return handle_create_invoice(event)
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
