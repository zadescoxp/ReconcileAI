"""
Fraud Detection Lambda Function
Detects potential fraud patterns in invoices including price spikes, unrecognized vendors,
duplicate invoices, and amount exceedances.
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Environment variables
POS_TABLE_NAME = os.environ['POS_TABLE_NAME']
INVOICES_TABLE_NAME = os.environ['INVOICES_TABLE_NAME']
AUDIT_LOGS_TABLE_NAME = os.environ['AUDIT_LOGS_TABLE_NAME']

# DynamoDB tables
pos_table = dynamodb.Table(POS_TABLE_NAME)
invoices_table = dynamodb.Table(INVOICES_TABLE_NAME)
audit_logs_table = dynamodb.Table(AUDIT_LOGS_TABLE_NAME)

# Fraud detection thresholds
PRICE_SPIKE_THRESHOLD = 0.20  # 20% above historical average
AMOUNT_EXCEEDANCE_THRESHOLD = 0.10  # 10% over PO total


class FraudDetectionError(Exception):
    """Base exception for fraud detection errors"""
    pass


class PermanentError(FraudDetectionError):
    """Permanent error that should not be retried"""
    pass


class RetryableError(FraudDetectionError):
    """Transient error that can be retried"""
    pass


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for fraud detection.
    
    Args:
        event: Step Functions input with invoice_id
        context: Lambda context
        
    Returns:
        Dict with invoice_id, fraud flags, and status
    """
    try:
        # Extract invoice ID from event
        invoice_id = event.get('invoice_id')
        
        if not invoice_id:
            raise PermanentError("Missing required field: invoice_id")
        
        print(f"Processing fraud detection for invoice {invoice_id}")
        
        # Retrieve invoice data from DynamoDB
        invoice = get_invoice_by_id(invoice_id)
        
        if not invoice:
            raise PermanentError(f"Invoice not found: {invoice_id}")
        
        # Update invoice status to DETECTING
        update_invoice_status(invoice_id, 'DETECTING')
        
        # Perform fraud detection checks
        fraud_flags = []
        
        # Check 1: Price spike detection
        price_spike_flags = check_price_spikes(invoice)
        fraud_flags.extend(price_spike_flags)
        
        # Check 2: Unrecognized vendor detection
        unrecognized_vendor_flag = check_unrecognized_vendor(invoice)
        if unrecognized_vendor_flag:
            fraud_flags.append(unrecognized_vendor_flag)
        
        # Check 3: Duplicate invoice detection
        duplicate_flag = check_duplicate_invoice(invoice)
        if duplicate_flag:
            fraud_flags.append(duplicate_flag)
        
        # Check 4: Amount exceedance detection
        amount_exceedance_flag = check_amount_exceedance(invoice)
        if amount_exceedance_flag:
            fraud_flags.append(amount_exceedance_flag)
        
        # Calculate risk score (0-100)
        risk_score = calculate_risk_score(fraud_flags)
        
        # Determine if manual review is required
        requires_review = len(fraud_flags) > 0
        
        # Store fraud flags in Invoices table
        store_fraud_flags(invoice_id, fraud_flags, risk_score)
        
        # Log fraud detection to audit trail
        log_audit_event(
            action_type="FraudDetected" if fraud_flags else "FraudCheckPassed",
            entity_id=invoice_id,
            details={
                "vendor_name": invoice.get('VendorName'),
                "invoice_number": invoice.get('InvoiceNumber'),
                "fraud_flags_count": len(fraud_flags),
                "risk_score": risk_score,
                "requires_review": requires_review,
                "fraud_flags": fraud_flags
            }
        )
        
        print(f"Fraud detection complete for invoice {invoice_id}: {len(fraud_flags)} flags, risk score {risk_score}")
        
        return {
            'statusCode': 200,
            'invoice_id': invoice_id,
            'status': 'DETECTING',
            'fraud_flags': fraud_flags,
            'risk_score': risk_score,
            'requires_review': requires_review
        }
        
    except PermanentError as e:
        # Log permanent error
        error_msg = f"Permanent fraud detection error: {str(e)}"
        print(error_msg)
        
        log_audit_event(
            action_type="FraudDetectionError",
            entity_id=event.get('invoice_id', 'unknown'),
            details={
                "error_type": "Permanent",
                "error_message": str(e)
            }
        )
        
        # Return error status (don't raise to avoid retries)
        return {
            'statusCode': 200,
            'status': 'FLAGGED',
            'error': str(e),
            'flagged_for_manual_review': True
        }
        
    except RetryableError as e:
        # Log retryable error and raise for Step Functions retry
        error_msg = f"Retryable fraud detection error: {str(e)}"
        print(error_msg)
        
        log_audit_event(
            action_type="FraudDetectionError",
            entity_id=event.get('invoice_id', 'unknown'),
            details={
                "error_type": "Retryable",
                "error_message": str(e)
            }
        )
        
        raise  # Re-raise for Step Functions retry
        
    except Exception as e:
        # Unexpected error - log and raise
        error_msg = f"Unexpected fraud detection error: {str(e)}"
        print(error_msg)
        
        log_audit_event(
            action_type="FraudDetectionError",
            entity_id=event.get('invoice_id', 'unknown'),
            details={
                "error_type": "Unexpected",
                "error_message": str(e)
            }
        )
        
        raise


def get_invoice_by_id(invoice_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve invoice from DynamoDB by ID."""
    try:
        response = invoices_table.get_item(Key={'InvoiceId': invoice_id})
        return response.get('Item')
    except ClientError as e:
        raise RetryableError(f"Failed to retrieve invoice: {str(e)}")


def update_invoice_status(invoice_id: str, status: str) -> None:
    """Update invoice status in DynamoDB."""
    try:
        invoices_table.update_item(
            Key={'InvoiceId': invoice_id},
            UpdateExpression='SET #status = :status',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={':status': status}
        )
    except ClientError as e:
        # Don't fail if status update fails
        print(f"Failed to update invoice status: {str(e)}")


def check_price_spikes(invoice: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Check for price spikes exceeding 20% above historical average.
    
    Returns list of fraud flags for items with price spikes.
    """
    fraud_flags = []
    vendor_name = invoice.get('VendorName')
    invoice_items = invoice.get('LineItems', [])
    
    # Get historical invoices for this vendor
    historical_invoices = get_historical_invoices(vendor_name, invoice.get('InvoiceId'))
    
    if not historical_invoices:
        # No historical data - cannot detect price spikes
        return fraud_flags
    
    # Build historical price map: item_description -> list of prices
    historical_prices = {}
    for hist_invoice in historical_invoices:
        for item in hist_invoice.get('LineItems', []):
            item_desc = item['item_description'].lower().strip()
            price = float(item['unit_price'])
            
            if item_desc not in historical_prices:
                historical_prices[item_desc] = []
            historical_prices[item_desc].append(price)
    
    # Check each invoice item against historical average
    for item in invoice_items:
        item_desc = item['item_description'].lower().strip()
        current_price = float(item['unit_price'])
        
        if item_desc in historical_prices:
            hist_prices = historical_prices[item_desc]
            avg_price = sum(hist_prices) / len(hist_prices)
            
            # Check if current price exceeds historical average by >20%
            if avg_price > 0:
                price_increase_pct = (current_price - avg_price) / avg_price
                
                if price_increase_pct > PRICE_SPIKE_THRESHOLD:
                    fraud_flags.append({
                        'flag_type': 'PRICE_SPIKE',
                        'severity': 'MEDIUM',
                        'description': f"Price spike detected for '{item['item_description']}': "
                                     f"${current_price:.2f} vs historical avg ${avg_price:.2f} "
                                     f"({price_increase_pct*100:.1f}% increase)",
                        'evidence': {
                            'item_description': item['item_description'],
                            'current_price': current_price,
                            'historical_average': avg_price,
                            'increase_percentage': price_increase_pct * 100,
                            'historical_sample_size': len(hist_prices)
                        }
                    })
    
    return fraud_flags


def check_unrecognized_vendor(invoice: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Check if vendor is unrecognized (no POs exist for this vendor).
    
    Returns fraud flag if vendor is unrecognized, None otherwise.
    """
    vendor_name = invoice.get('VendorName')
    
    # Handle empty or missing vendor name
    if not vendor_name or vendor_name.strip() == '':
        return {
            'flag_type': 'UNRECOGNIZED_VENDOR',
            'severity': 'HIGH',
            'description': f"Unrecognized vendor: empty or missing vendor name",
            'evidence': {
                'vendor_name': vendor_name or '',
                'po_count': 0
            }
        }
    
    # Check if any POs exist for this vendor
    try:
        response = pos_table.query(
            IndexName='VendorNameIndex',
            KeyConditionExpression='VendorName = :vendor_name',
            ExpressionAttributeValues={':vendor_name': vendor_name},
            Limit=1  # Just need to know if any exist
        )
        
        pos = response.get('Items', [])
        
        if not pos or len(pos) == 0:
            return {
                'flag_type': 'UNRECOGNIZED_VENDOR',
                'severity': 'HIGH',
                'description': f"Unrecognized vendor: '{vendor_name}' has no purchase orders in the system",
                'evidence': {
                    'vendor_name': vendor_name,
                    'po_count': 0
                }
            }
        
        return None
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ProvisionedThroughputExceededException':
            raise RetryableError(f"DynamoDB throttling: {str(e)}")
        else:
            raise RetryableError(f"Failed to query POs: {str(e)}")


def check_duplicate_invoice(invoice: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Check for duplicate invoice numbers for the same vendor.
    
    Returns fraud flag if duplicate is found, None otherwise.
    """
    vendor_name = invoice.get('VendorName')
    invoice_number = invoice.get('InvoiceNumber')
    current_invoice_id = invoice.get('InvoiceId')
    
    # Query invoices by vendor name
    try:
        response = invoices_table.query(
            IndexName='VendorNameIndex',
            KeyConditionExpression='VendorName = :vendor_name',
            ExpressionAttributeValues={':vendor_name': vendor_name}
        )
        
        invoices = response.get('Items', [])
        
        # Check for duplicate invoice numbers (excluding current invoice)
        for inv in invoices:
            if inv.get('InvoiceId') != current_invoice_id and inv.get('InvoiceNumber') == invoice_number:
                return {
                    'flag_type': 'DUPLICATE_INVOICE',
                    'severity': 'HIGH',
                    'description': f"Duplicate invoice number detected: '{invoice_number}' already exists for vendor '{vendor_name}'",
                    'evidence': {
                        'vendor_name': vendor_name,
                        'invoice_number': invoice_number,
                        'duplicate_invoice_id': inv.get('InvoiceId'),
                        'duplicate_received_date': inv.get('ReceivedDate')
                    }
                }
        
        return None
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ProvisionedThroughputExceededException':
            raise RetryableError(f"DynamoDB throttling: {str(e)}")
        else:
            raise RetryableError(f"Failed to query invoices: {str(e)}")


def check_amount_exceedance(invoice: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Check if invoice total exceeds matched PO total by more than 10%.
    
    Returns fraud flag if amount exceedance is detected, None otherwise.
    """
    matched_po_ids = invoice.get('MatchedPOIds', [])
    
    if not matched_po_ids or len(matched_po_ids) == 0:
        # No matched POs - cannot check amount exceedance
        return None
    
    invoice_total = float(invoice.get('TotalAmount', 0))
    
    # Get matched POs and calculate total
    try:
        po_total = 0.0
        for po_id in matched_po_ids:
            response = pos_table.get_item(Key={'POId': po_id})
            po = response.get('Item')
            
            if po:
                po_total += float(po.get('TotalAmount', 0))
        
        if po_total > 0:
            exceedance_pct = (invoice_total - po_total) / po_total
            
            if exceedance_pct > AMOUNT_EXCEEDANCE_THRESHOLD:
                return {
                    'flag_type': 'AMOUNT_EXCEEDED',
                    'severity': 'MEDIUM',
                    'description': f"Invoice total ${invoice_total:.2f} exceeds PO total ${po_total:.2f} by {exceedance_pct*100:.1f}%",
                    'evidence': {
                        'invoice_total': invoice_total,
                        'po_total': po_total,
                        'exceedance_percentage': exceedance_pct * 100,
                        'matched_po_ids': matched_po_ids
                    }
                }
        
        return None
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ProvisionedThroughputExceededException':
            raise RetryableError(f"DynamoDB throttling: {str(e)}")
        else:
            raise RetryableError(f"Failed to retrieve POs: {str(e)}")


def get_historical_invoices(vendor_name: str, exclude_invoice_id: str) -> List[Dict[str, Any]]:
    """
    Get historical invoices for a vendor (excluding current invoice).
    Used for price spike detection.
    """
    try:
        response = invoices_table.query(
            IndexName='VendorNameIndex',
            KeyConditionExpression='VendorName = :vendor_name',
            ExpressionAttributeValues={':vendor_name': vendor_name},
            Limit=20  # Limit to 20 most recent invoices
        )
        
        invoices = response.get('Items', [])
        
        # Filter out current invoice
        historical = [inv for inv in invoices if inv.get('InvoiceId') != exclude_invoice_id]
        
        return historical
        
    except ClientError as e:
        # If query fails, return empty list (cannot detect price spikes)
        print(f"Failed to query historical invoices: {str(e)}")
        return []


def calculate_risk_score(fraud_flags: List[Dict[str, Any]]) -> int:
    """
    Calculate risk score (0-100) based on fraud flags.
    
    Severity weights:
    - HIGH: 40 points
    - MEDIUM: 25 points
    - LOW: 10 points
    """
    severity_weights = {
        'HIGH': 40,
        'MEDIUM': 25,
        'LOW': 10
    }
    
    score = 0
    for flag in fraud_flags:
        severity = flag.get('severity', 'LOW')
        score += severity_weights.get(severity, 10)
    
    # Cap at 100
    return min(score, 100)


def store_fraud_flags(invoice_id: str, fraud_flags: List[Dict[str, Any]], risk_score: int) -> None:
    """Store fraud flags in DynamoDB Invoices table."""
    try:
        invoices_table.update_item(
            Key={'InvoiceId': invoice_id},
            UpdateExpression='SET FraudFlags = :fraud_flags, #status = :status',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={
                ':fraud_flags': fraud_flags,
                ':status': 'FLAGGED' if fraud_flags else 'APPROVED'
            }
        )
        
        print(f"Stored {len(fraud_flags)} fraud flags for invoice {invoice_id}")
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ProvisionedThroughputExceededException':
            raise RetryableError(f"DynamoDB throttling: {str(e)}")
        else:
            raise RetryableError(f"Failed to store fraud flags: {str(e)}")


def log_audit_event(action_type: str, entity_id: str, details: Dict[str, Any]) -> None:
    """Log an event to the audit trail."""
    try:
        log_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        audit_logs_table.put_item(
            Item={
                'LogId': log_id,
                'Timestamp': timestamp,
                'Actor': 'System',
                'ActionType': action_type,
                'EntityType': 'Invoice',
                'EntityId': entity_id,
                'Details': details,
                'Reasoning': ''
            }
        )
    except Exception as e:
        # Don't fail the main operation if audit logging fails
        print(f"Failed to log audit event: {str(e)}")
