"""
Resolve Step Lambda Function
Implements auto-approval logic for clean invoices or flags for human review.

Requirements: 9.1, 9.2, 9.3, 9.4, 7.5
"""

import json
import os
import boto3
from datetime import datetime
from decimal import Decimal
import uuid

# Initialize AWS clients lazily
_dynamodb = None
_invoices_table = None
_audit_logs_table = None


def get_dynamodb_resource():
    """Get or create DynamoDB resource"""
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource('dynamodb')
    return _dynamodb


def get_invoices_table():
    """Get or create Invoices table"""
    global _invoices_table
    if _invoices_table is None:
        dynamodb = get_dynamodb_resource()
        _invoices_table = dynamodb.Table(os.environ['INVOICES_TABLE_NAME'])
    return _invoices_table


def get_audit_logs_table():
    """Get or create AuditLogs table"""
    global _audit_logs_table
    if _audit_logs_table is None:
        dynamodb = get_dynamodb_resource()
        _audit_logs_table = dynamodb.Table(os.environ['AUDIT_LOGS_TABLE_NAME'])
    return _audit_logs_table


class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert Decimal to float for JSON serialization"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def log_audit_entry(actor, action_type, entity_id, details, reasoning=None):
    """Log an action to the audit trail"""
    audit_logs_table = get_audit_logs_table()
    
    log_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    # Convert floats to Decimal for DynamoDB compatibility
    def convert_floats(obj):
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: convert_floats(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_floats(item) for item in obj]
        return obj
    
    details = convert_floats(details)
    
    entry = {
        'LogId': log_id,
        'Timestamp': timestamp,
        'Actor': actor,
        'ActionType': action_type,
        'EntityType': 'Invoice',
        'EntityId': entity_id,
        'Details': details,
    }
    
    if reasoning:
        entry['Reasoning'] = reasoning
    
    audit_logs_table.put_item(Item=entry)
    return log_id


def lambda_handler(event, context):
    """
    Resolve step: Auto-approve clean invoices or flag for human review
    
    Input:
        - invoice_id: Invoice identifier
        - discrepancies: List of discrepancies from matching step
        - fraud_flags: List of fraud flags from detection step
    
    Output:
        - invoice_id: Invoice identifier
        - status: "Approved" or "Flagged"
        - requires_review: Boolean
        - reasoning: Explanation of decision
    """
    
    try:
        # Get DynamoDB tables
        invoices_table = get_invoices_table()
        
        # Extract invoice data from event
        invoice_id = event.get('invoice_id')
        discrepancies = event.get('discrepancies', [])
        fraud_flags = event.get('fraud_flags', [])
        
        if not invoice_id:
            raise ValueError("Missing required field: invoice_id")
        
        # Retrieve invoice from DynamoDB
        response = invoices_table.get_item(Key={'InvoiceId': invoice_id})
        
        if 'Item' not in response:
            raise ValueError(f"Invoice not found: {invoice_id}")
        
        invoice = response['Item']
        
        # Check if invoice has zero discrepancies and zero fraud flags
        has_discrepancies = len(discrepancies) > 0
        has_fraud_flags = len(fraud_flags) > 0
        
        if not has_discrepancies and not has_fraud_flags:
            # Auto-approve clean invoice (Requirement 9.1)
            new_status = 'Approved'
            requires_review = False
            reasoning = (
                "Invoice automatically approved: "
                "All line items matched within acceptable tolerances, "
                "no discrepancies detected, and no fraud flags raised."
            )
            
            # Update invoice status to "Approved" (Requirement 9.3)
            invoices_table.update_item(
                Key={'InvoiceId': invoice_id},
                UpdateExpression='SET #status = :status, ApprovedDate = :approved_date',
                ExpressionAttributeNames={'#status': 'Status'},
                ExpressionAttributeValues={
                    ':status': new_status,
                    ':approved_date': datetime.utcnow().isoformat() + 'Z',
                }
            )
            
            # Log auto-approval to audit trail (Requirement 9.2, 10.1)
            log_audit_entry(
                actor='System',
                action_type='InvoiceApproved',
                entity_id=invoice_id,
                details={
                    'approval_type': 'automatic',
                    'vendor_name': invoice.get('VendorName'),
                    'invoice_number': invoice.get('InvoiceNumber'),
                    'total_amount': float(invoice.get('TotalAmount', 0)),
                    'matched_po_ids': invoice.get('MatchedPOIds', []),
                },
                reasoning=reasoning
            )
            
        else:
            # Flag for human approval (Requirement 7.5, 8.1)
            new_status = 'Flagged'
            requires_review = True
            
            # Build reasoning for flagging
            reasons = []
            if has_discrepancies:
                reasons.append(f"{len(discrepancies)} discrepancy(ies) detected")
            if has_fraud_flags:
                reasons.append(f"{len(fraud_flags)} fraud flag(s) raised")
            
            reasoning = (
                f"Invoice flagged for human review: {', '.join(reasons)}. "
                "Manual approval required before proceeding with payment."
            )
            
            # Update invoice status to "Flagged"
            invoices_table.update_item(
                Key={'InvoiceId': invoice_id},
                UpdateExpression='SET #status = :status, FlaggedDate = :flagged_date',
                ExpressionAttributeNames={'#status': 'Status'},
                ExpressionAttributeValues={
                    ':status': new_status,
                    ':flagged_date': datetime.utcnow().isoformat() + 'Z',
                }
            )
            
            # Log flagging to audit trail
            log_audit_entry(
                actor='System',
                action_type='InvoiceFlagged',
                entity_id=invoice_id,
                details={
                    'vendor_name': invoice.get('VendorName'),
                    'invoice_number': invoice.get('InvoiceNumber'),
                    'total_amount': float(invoice.get('TotalAmount', 0)),
                    'discrepancy_count': len(discrepancies),
                    'fraud_flag_count': len(fraud_flags),
                    'discrepancies': discrepancies,
                    'fraud_flags': fraud_flags,
                },
                reasoning=reasoning
            )
        
        # Return result
        result = {
            'invoice_id': invoice_id,
            'status': new_status,
            'requires_review': requires_review,
            'reasoning': reasoning,
            'discrepancy_count': len(discrepancies),
            'fraud_flag_count': len(fraud_flags),
        }
        
        print(f"Resolve step completed: {json.dumps(result, cls=DecimalEncoder)}")
        
        return result
        
    except Exception as e:
        error_msg = f"Error in resolve step: {str(e)}"
        print(error_msg)
        
        # Log error to audit trail
        try:
            invoice_id_for_log = event.get('invoice_id') if event else None
            if invoice_id_for_log:
                log_audit_entry(
                    actor='System',
                    action_type='ProcessingError',
                    entity_id=invoice_id_for_log,
                    details={
                        'error': str(e),
                        'step': 'resolve',
                    }
                )
        except:
            pass  # Don't fail if audit logging fails
        
        raise
