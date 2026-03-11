"""
CSV Processor Lambda
Processes CSV invoices and POs uploaded to S3
"""

import json
import os
import uuid
import csv
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any
import boto3
from botocore.exceptions import ClientError
from io import StringIO

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sfn_client = boto3.client('stepfunctions')

# Environment variables
INVOICES_TABLE_NAME = os.environ['INVOICES_TABLE_NAME']
AUDIT_LOGS_TABLE_NAME = os.environ['AUDIT_LOGS_TABLE_NAME']
STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']

# DynamoDB tables
invoices_table = dynamodb.Table(INVOICES_TABLE_NAME)
audit_logs_table = dynamodb.Table(AUDIT_LOGS_TABLE_NAME)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for CSV processing.
    """
    try:
        for record in event.get('Records', []):
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            print(f"Processing CSV: s3://{bucket}/{key}")
            
            # Download CSV from S3
            response = s3_client.get_object(Bucket=bucket, Key=key)
            csv_content = response['Body'].read().decode('utf-8')
            
            # Parse CSV
            invoice_data = parse_csv_invoice(csv_content)
            
            print(f"Parsed invoice data: {json.dumps(invoice_data, default=str)}")
            
            # Generate invoice ID
            invoice_id = str(uuid.uuid4())
            
            # Store invoice data in DynamoDB
            store_invoice_data(invoice_id, invoice_data, bucket, key)
            
            # Log extraction to audit trail
            log_audit_event(
                action_type="InvoiceExtracted",
                entity_id=invoice_id,
                details={
                    "s3_bucket": bucket,
                    "s3_key": key,
                    "vendor_name": invoice_data.get('vendor_name'),
                    "invoice_number": invoice_data.get('invoice_number'),
                    "total_amount": invoice_data.get('total_amount'),
                    "line_items_count": len(invoice_data.get('line_items', []))
                }
            )
            
            print(f"Successfully processed CSV invoice {invoice_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps('CSV processed successfully')
        }
        
    except Exception as e:
        print(f"Error processing CSV: {str(e)}")
        raise


def parse_csv_invoice(csv_content: str) -> Dict[str, Any]:
    """Parse invoice data from CSV content"""
    invoice_data = {
        'invoice_number': None,
        'vendor_name': None,
        'invoice_date': None,
        'line_items': [],
        'total_amount': None
    }
    
    reader = csv.reader(StringIO(csv_content))
    rows = list(reader)
    
    # Parse header section
    for i, row in enumerate(rows):
        if len(row) < 2:
            continue
            
        key = row[0].strip().lower()
        value = row[1].strip() if len(row) > 1 else ''
        
        if 'invoice number' in key or 'po number' in key:
            invoice_data['invoice_number'] = value
        elif 'vendor' in key:
            invoice_data['vendor_name'] = value
        elif 'date' in key:
            invoice_data['invoice_date'] = value
        elif 'total amount' in key:
            # Remove $ and commas
            amount_str = value.replace('$', '').replace(',', '')
            try:
                invoice_data['total_amount'] = Decimal(amount_str)
            except:
                pass
    
    # Parse line items
    line_items_start = -1
    for i, row in enumerate(rows):
        if len(row) > 0 and 'item description' in row[0].lower():
            line_items_start = i + 1
            break
    
    if line_items_start > 0:
        for i in range(line_items_start, len(rows)):
            row = rows[i]
            if len(row) < 5:
                continue
            
            # Skip empty rows or total rows
            if not row[0] or 'total' in row[0].lower():
                continue
            
            try:
                line_number = int(row[0])
                item_description = row[1]
                quantity = int(row[2])
                unit_price_str = row[3].replace('$', '').replace(',', '')
                total_price_str = row[4].replace('$', '').replace(',', '')
                
                unit_price = Decimal(unit_price_str)
                total_price = Decimal(total_price_str)
                
                invoice_data['line_items'].append({
                    'item_description': item_description,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'total_price': total_price
                })
            except (ValueError, IndexError) as e:
                print(f"Skipping row {i}: {str(e)}")
                continue
    
    return invoice_data


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
        print(f"Failed to store invoice data: {str(e)}")
        raise


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
        print(f"Failed to log audit event: {str(e)}")
