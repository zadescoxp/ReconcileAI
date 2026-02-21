"""
PDF Extraction Lambda Function
Extracts text and structured data from invoice PDFs stored in S3.
"""

import json
import os
import uuid
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import boto3
from botocore.exceptions import ClientError
import pdfplumber

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
INVOICES_TABLE_NAME = os.environ['INVOICES_TABLE_NAME']
AUDIT_LOGS_TABLE_NAME = os.environ['AUDIT_LOGS_TABLE_NAME']

# DynamoDB tables
invoices_table = dynamodb.Table(INVOICES_TABLE_NAME)
audit_logs_table = dynamodb.Table(AUDIT_LOGS_TABLE_NAME)


class PDFExtractionError(Exception):
    """Base exception for PDF extraction errors"""
    pass


class PermanentError(PDFExtractionError):
    """Permanent error that should not be retried"""
    pass


class RetryableError(PDFExtractionError):
    """Transient error that can be retried"""
    pass


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for PDF extraction.
    
    Args:
        event: Step Functions input with s3_bucket and s3_key
        context: Lambda context
        
    Returns:
        Dict with invoice_id and status
    """
    try:
        # Extract S3 details from event
        s3_bucket = event.get('s3_bucket')
        s3_key = event.get('s3_key')
        
        if not s3_bucket or not s3_key:
            raise PermanentError(f"Missing required fields: s3_bucket={s3_bucket}, s3_key={s3_key}")
        
        print(f"Processing PDF: s3://{s3_bucket}/{s3_key}")
        
        # Download PDF from S3
        pdf_content = download_pdf_from_s3(s3_bucket, s3_key)
        
        # Extract text from PDF
        extracted_text = extract_text_from_pdf(pdf_content)
        
        if not extracted_text or len(extracted_text.strip()) < 10:
            raise PermanentError("PDF contains no extractable text or text is too short")
        
        # Parse invoice data from extracted text
        invoice_data = parse_invoice_data(extracted_text)
        
        # Validate required fields
        validate_invoice_data(invoice_data)
        
        # Generate invoice ID
        invoice_id = str(uuid.uuid4())
        
        # Store invoice data in DynamoDB
        store_invoice_data(invoice_id, invoice_data, s3_bucket, s3_key)
        
        # Log extraction to audit trail
        log_audit_event(
            action_type="InvoiceExtracted",
            entity_id=invoice_id,
            details={
                "s3_bucket": s3_bucket,
                "s3_key": s3_key,
                "vendor_name": invoice_data.get('vendor_name'),
                "invoice_number": invoice_data.get('invoice_number'),
                "total_amount": invoice_data.get('total_amount'),
                "line_items_count": len(invoice_data.get('line_items', []))
            }
        )
        
        print(f"Successfully extracted invoice {invoice_id}")
        
        return {
            'statusCode': 200,
            'invoice_id': invoice_id,
            'status': 'EXTRACTING',
            'vendor_name': invoice_data.get('vendor_name'),
            's3_bucket': s3_bucket,
            's3_key': s3_key
        }
        
    except PermanentError as e:
        # Log permanent error
        error_msg = f"Permanent extraction error: {str(e)}"
        print(error_msg)
        
        log_audit_event(
            action_type="ExtractionError",
            entity_id=event.get('s3_key', 'unknown'),
            details={
                "error_type": "Permanent",
                "error_message": str(e),
                "s3_bucket": event.get('s3_bucket'),
                "s3_key": event.get('s3_key')
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
        error_msg = f"Retryable extraction error: {str(e)}"
        print(error_msg)
        
        log_audit_event(
            action_type="ExtractionError",
            entity_id=event.get('s3_key', 'unknown'),
            details={
                "error_type": "Retryable",
                "error_message": str(e),
                "s3_bucket": event.get('s3_bucket'),
                "s3_key": event.get('s3_key')
            }
        )
        
        raise  # Re-raise for Step Functions retry
        
    except Exception as e:
        # Unexpected error - log and raise
        error_msg = f"Unexpected extraction error: {str(e)}"
        print(error_msg)
        
        log_audit_event(
            action_type="ExtractionError",
            entity_id=event.get('s3_key', 'unknown'),
            details={
                "error_type": "Unexpected",
                "error_message": str(e),
                "s3_bucket": event.get('s3_bucket'),
                "s3_key": event.get('s3_key')
            }
        )
        
        raise


def download_pdf_from_s3(bucket: str, key: str) -> bytes:
    """Download PDF file from S3."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            raise PermanentError(f"PDF not found in S3: {bucket}/{key}")
        elif error_code in ['ServiceUnavailable', 'SlowDown']:
            raise RetryableError(f"S3 service temporarily unavailable: {error_code}")
        else:
            raise RetryableError(f"Failed to download PDF from S3: {str(e)}")


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import io
        pdf_file = io.BytesIO(pdf_content)
        
        extracted_text = ""
        with pdfplumber.open(pdf_file) as pdf:
            if len(pdf.pages) == 0:
                raise PermanentError("PDF has no pages")
            
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
        
        return extracted_text.strip()
        
    except Exception as e:
        raise PermanentError(f"Failed to extract text from PDF: {str(e)}")


def parse_invoice_data(text: str) -> Dict[str, Any]:
    """
    Parse invoice data from extracted text.
    Uses regex patterns to identify invoice fields.
    """
    invoice_data = {
        'invoice_number': None,
        'vendor_name': None,
        'invoice_date': None,
        'line_items': [],
        'total_amount': None,
        'raw_text': text
    }
    
    # Parse invoice number
    invoice_number_patterns = [
        r'invoice\s*#?\s*:?\s*([A-Z0-9\-]+)',
        r'invoice\s+number\s*:?\s*([A-Z0-9\-]+)',
        r'inv\s*#?\s*:?\s*([A-Z0-9\-]+)',
    ]
    for pattern in invoice_number_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            invoice_data['invoice_number'] = match.group(1).strip()
            break
    
    # Parse vendor name (usually at the top of the invoice)
    vendor_patterns = [
        r'from\s*:?\s*([A-Za-z0-9\s&\.,]+?)(?:\n|$)',
        r'vendor\s*:?\s*([A-Za-z0-9\s&\.,]+?)(?:\n|$)',
        r'^([A-Z][A-Za-z0-9\s&\.,]{3,50}?)(?:\n)',
    ]
    for pattern in vendor_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            vendor_name = match.group(1).strip()
            # Clean up vendor name
            vendor_name = re.sub(r'\s+', ' ', vendor_name)
            if len(vendor_name) > 3:
                invoice_data['vendor_name'] = vendor_name
                break
    
    # Parse invoice date
    date_patterns = [
        r'date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'invoice\s+date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            invoice_data['invoice_date'] = match.group(1).strip()
            break
    
    # Parse total amount
    total_patterns = [
        r'total\s*:?\s*\$?\s*([\d,]+\.?\d{0,2})',
        r'amount\s+due\s*:?\s*\$?\s*([\d,]+\.?\d{0,2})',
        r'grand\s+total\s*:?\s*\$?\s*([\d,]+\.?\d{0,2})',
    ]
    for pattern in total_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                invoice_data['total_amount'] = float(amount_str)
                break
            except ValueError:
                continue
    
    # Parse line items (simplified pattern)
    # Look for patterns like: "Item description  Qty  Price  Total"
    line_item_pattern = r'([A-Za-z0-9\s\-,\.]+?)\s+(\d+)\s+\$?([\d,]+\.?\d{0,2})\s+\$?([\d,]+\.?\d{0,2})'
    matches = re.finditer(line_item_pattern, text)
    
    for match in matches:
        try:
            item_description = match.group(1).strip()
            quantity = int(match.group(2))
            unit_price = float(match.group(3).replace(',', ''))
            total_price = float(match.group(4).replace(',', ''))
            
            # Basic validation
            if len(item_description) > 3 and quantity > 0 and unit_price > 0:
                invoice_data['line_items'].append({
                    'item_description': item_description,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'total_price': total_price
                })
        except (ValueError, IndexError):
            continue
    
    return invoice_data


def validate_invoice_data(invoice_data: Dict[str, Any]) -> None:
    """Validate that invoice data contains required fields."""
    required_fields = ['invoice_number', 'vendor_name', 'invoice_date', 'total_amount']
    missing_fields = []
    
    for field in required_fields:
        if not invoice_data.get(field):
            missing_fields.append(field)
    
    if missing_fields:
        raise PermanentError(f"Missing required invoice fields: {', '.join(missing_fields)}")
    
    # Validate line items
    if not invoice_data.get('line_items') or len(invoice_data['line_items']) == 0:
        raise PermanentError("No line items found in invoice")


def store_invoice_data(invoice_id: str, invoice_data: Dict[str, Any], s3_bucket: str, s3_key: str) -> None:
    """Store extracted invoice data in DynamoDB."""
    try:
        item = {
            'InvoiceId': invoice_id,
            'VendorName': invoice_data['vendor_name'],
            'InvoiceNumber': invoice_data['invoice_number'],
            'InvoiceDate': invoice_data['invoice_date'],
            'LineItems': invoice_data['line_items'],
            'TotalAmount': invoice_data['total_amount'],
            'Status': 'EXTRACTING',
            'ReceivedDate': datetime.utcnow().isoformat(),
            'S3Key': s3_key,
            'S3Bucket': s3_bucket,
            'MatchedPOIds': [],
            'Discrepancies': [],
            'FraudFlags': [],
            'AIReasoning': '',
            'StepFunctionArn': ''
        }
        
        invoices_table.put_item(Item=item)
        print(f"Stored invoice data for {invoice_id}")
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ProvisionedThroughputExceededException':
            raise RetryableError(f"DynamoDB throttling: {str(e)}")
        else:
            raise RetryableError(f"Failed to store invoice data: {str(e)}")


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
