"""
AI Matching Lambda Function
Uses Amazon Bedrock Claude 3 Haiku to match invoice line items against purchase orders.
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from difflib import SequenceMatcher

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
dynamodb = boto3.resource('dynamodb')

# Environment variables
POS_TABLE_NAME = os.environ['POS_TABLE_NAME']
INVOICES_TABLE_NAME = os.environ['INVOICES_TABLE_NAME']
AUDIT_LOGS_TABLE_NAME = os.environ['AUDIT_LOGS_TABLE_NAME']

# DynamoDB tables
pos_table = dynamodb.Table(POS_TABLE_NAME)
invoices_table = dynamodb.Table(INVOICES_TABLE_NAME)
audit_logs_table = dynamodb.Table(AUDIT_LOGS_TABLE_NAME)

# Constants
BEDROCK_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
PRICE_TOLERANCE = 0.05  # ±5% price tolerance for perfect match
PRICE_TOLERANCE_EPSILON = 0.001  # Small epsilon for floating-point precision
MAX_TOKENS = 2000  # Limit response length to save costs


class AIMatchingError(Exception):
    """Base exception for AI matching errors"""
    pass


class PermanentError(AIMatchingError):
    """Permanent error that should not be retried"""
    pass


class RetryableError(AIMatchingError):
    """Transient error that can be retried"""
    pass


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for AI matching.
    
    Args:
        event: Step Functions input with invoice_id
        context: Lambda context
        
    Returns:
        Dict with invoice_id, match results, and status
    """
    try:
        # Extract invoice ID from event
        invoice_id = event.get('invoice_id')
        
        if not invoice_id:
            raise PermanentError("Missing required field: invoice_id")
        
        print(f"Processing AI matching for invoice {invoice_id}")
        
        # Retrieve invoice data from DynamoDB
        invoice = get_invoice_by_id(invoice_id)
        
        if not invoice:
            raise PermanentError(f"Invoice not found: {invoice_id}")
        
        # Update invoice status to MATCHING
        update_invoice_status(invoice_id, 'MATCHING')
        
        # Query relevant POs from DynamoDB
        vendor_name = invoice.get('VendorName')
        invoice_date = invoice.get('InvoiceDate')
        relevant_pos = query_relevant_pos(vendor_name, invoice_date)
        
        if not relevant_pos:
            # No matching POs found - this will be flagged as unrecognized vendor in fraud detection
            print(f"No POs found for vendor: {vendor_name}")
            match_result = {
                'matched_po_ids': [],
                'discrepancies': [],
                'confidence_score': 0,
                'reasoning': f"No purchase orders found for vendor '{vendor_name}'",
                'is_perfect_match': False
            }
        else:
            # Call Bedrock API for AI matching
            match_result = perform_ai_matching(invoice, relevant_pos)
        
        # Store match results in Invoices table
        store_match_results(invoice_id, match_result)
        
        # Log AI decision to audit trail
        log_audit_event(
            action_type="InvoiceMatched",
            entity_id=invoice_id,
            details={
                "vendor_name": vendor_name,
                "matched_po_ids": match_result['matched_po_ids'],
                "discrepancies_count": len(match_result['discrepancies']),
                "confidence_score": match_result['confidence_score'],
                "is_perfect_match": match_result['is_perfect_match']
            },
            reasoning=match_result['reasoning']
        )
        
        print(f"Successfully matched invoice {invoice_id}")
        
        return {
            'statusCode': 200,
            'invoice_id': invoice_id,
            'status': 'MATCHING',
            'matched_po_ids': match_result['matched_po_ids'],
            'discrepancies': match_result['discrepancies'],
            'is_perfect_match': match_result['is_perfect_match'],
            'confidence_score': match_result['confidence_score']
        }
        
    except PermanentError as e:
        # Log permanent error
        error_msg = f"Permanent matching error: {str(e)}"
        print(error_msg)
        
        log_audit_event(
            action_type="MatchingError",
            entity_id=event.get('invoice_id', 'unknown'),
            details={
                "error_type": "Permanent",
                "error_message": str(e)
            },
            reasoning=""
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
        error_msg = f"Retryable matching error: {str(e)}"
        print(error_msg)
        
        log_audit_event(
            action_type="MatchingError",
            entity_id=event.get('invoice_id', 'unknown'),
            details={
                "error_type": "Retryable",
                "error_message": str(e)
            },
            reasoning=""
        )
        
        raise  # Re-raise for Step Functions retry
        
    except Exception as e:
        # Unexpected error - log and raise
        error_msg = f"Unexpected matching error: {str(e)}"
        print(error_msg)
        
        log_audit_event(
            action_type="MatchingError",
            entity_id=event.get('invoice_id', 'unknown'),
            details={
                "error_type": "Unexpected",
                "error_message": str(e)
            },
            reasoning=""
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


def query_relevant_pos(vendor_name: str, invoice_date: str) -> List[Dict[str, Any]]:
    """
    Query relevant POs from DynamoDB by vendor name.
    Returns POs from the same vendor within a reasonable date range.
    """
    try:
        # Parse invoice date to determine date range
        # For simplicity, query all POs for the vendor (can be optimized with date range)
        response = pos_table.query(
            IndexName='VendorNameIndex',
            KeyConditionExpression='VendorName = :vendor_name',
            ExpressionAttributeValues={':vendor_name': vendor_name},
            Limit=10  # Limit to 10 most recent POs to save on Bedrock token costs
        )
        
        pos = response.get('Items', [])
        print(f"Found {len(pos)} POs for vendor: {vendor_name}")
        return pos
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ProvisionedThroughputExceededException':
            raise RetryableError(f"DynamoDB throttling: {str(e)}")
        else:
            raise RetryableError(f"Failed to query POs: {str(e)}")


def perform_ai_matching(invoice: Dict[str, Any], pos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Perform AI matching using Amazon Bedrock Claude 3 Haiku.
    
    Args:
        invoice: Invoice data from DynamoDB
        pos: List of relevant POs
        
    Returns:
        Match result with matched PO IDs, discrepancies, confidence, and reasoning
    """
    # Build concise prompt
    prompt = build_matching_prompt(invoice, pos)
    
    # Call Bedrock API
    bedrock_response = call_bedrock_api(prompt)
    
    # Parse Bedrock response
    match_result = parse_bedrock_response(bedrock_response, invoice, pos)
    
    # Classify as perfect match if applicable
    match_result['is_perfect_match'] = classify_perfect_match(
        invoice, pos, match_result['matched_po_ids'], match_result['discrepancies']
    )
    
    return match_result


def build_matching_prompt(invoice: Dict[str, Any], pos: List[Dict[str, Any]]) -> str:
    """Build concise prompt for Bedrock API."""
    # Format invoice data
    invoice_lines = []
    for idx, item in enumerate(invoice.get('LineItems', []), 1):
        invoice_lines.append(
            f"  {idx}. {item['item_description']} | Qty: {item['quantity']} | "
            f"Unit Price: ${item['unit_price']:.2f} | Total: ${item['total_price']:.2f}"
        )
    
    invoice_section = f"""INVOICE:
- Number: {invoice.get('InvoiceNumber')}
- Vendor: {invoice.get('VendorName')}
- Date: {invoice.get('InvoiceDate')}
- Line Items:
{chr(10).join(invoice_lines)}
- Total: ${invoice.get('TotalAmount', 0):.2f}"""
    
    # Format PO data (concise)
    po_sections = []
    for po in pos[:5]:  # Limit to 5 POs to save tokens
        po_lines = []
        for idx, item in enumerate(po.get('LineItems', [])[:10], 1):  # Limit to 10 items per PO
            po_lines.append(
                f"  {idx}. {item['ItemDescription']} | Qty: {item['Quantity']} | "
                f"Unit Price: ${float(item['UnitPrice']):.2f}"
            )
        
        po_sections.append(f"""PO {po.get('PONumber')} (ID: {po.get('POId')}):
{chr(10).join(po_lines)}
Total: ${float(po.get('TotalAmount', 0)):.2f}""")
    
    pos_section = "\n\n".join(po_sections)
    
    # Build full prompt
    prompt = f"""You are an accounts payable clerk matching an invoice to purchase orders.

{invoice_section}

PURCHASE ORDERS:
{pos_section}

TASK:
1. Match each invoice line item to PO line items
2. Identify discrepancies (price differences >5%, quantity mismatches, missing items)
3. Calculate confidence score (0-100)
4. Provide step-by-step reasoning

Respond ONLY with valid JSON (no markdown):
{{
  "matched_po_ids": ["PO_ID1"],
  "line_matches": [
    {{
      "invoice_line": 1,
      "po_id": "PO_ID",
      "po_line": 1,
      "match_confidence": 95,
      "discrepancies": []
    }}
  ],
  "overall_confidence": 90,
  "reasoning": "Step-by-step explanation",
  "discrepancies": [
    {{
      "type": "PRICE_MISMATCH",
      "invoice_line": 1,
      "po_line": 1,
      "difference": 5.50,
      "description": "Price difference of $5.50"
    }}
  ]
}}"""
    
    return prompt


def call_bedrock_api(prompt: str) -> str:
    """Call Amazon Bedrock Claude 3 Haiku API."""
    try:
        # Prepare request body
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": MAX_TOKENS,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,  # Low temperature for consistent matching
            "top_p": 0.9
        }
        
        # Invoke Bedrock model
        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        
        # Extract text from response
        if 'content' in response_body and len(response_body['content']) > 0:
            return response_body['content'][0]['text']
        else:
            raise PermanentError("Empty response from Bedrock API")
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code in ['ThrottlingException', 'ServiceUnavailable']:
            raise RetryableError(f"Bedrock API temporarily unavailable: {error_code}")
        else:
            raise RetryableError(f"Bedrock API error: {str(e)}")
    except Exception as e:
        raise RetryableError(f"Failed to call Bedrock API: {str(e)}")


def parse_bedrock_response(response_text: str, invoice: Dict[str, Any], pos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Parse Bedrock JSON response."""
    try:
        # Remove markdown code blocks if present
        response_text = response_text.strip()
        if response_text.startswith('```'):
            # Remove ```json and ``` markers
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
        
        # Parse JSON
        parsed = json.loads(response_text)
        
        # Extract and validate fields
        match_result = {
            'matched_po_ids': parsed.get('matched_po_ids', []),
            'discrepancies': parsed.get('discrepancies', []),
            'confidence_score': parsed.get('overall_confidence', 0),
            'reasoning': parsed.get('reasoning', ''),
            'line_matches': parsed.get('line_matches', [])
        }
        
        return match_result
        
    except json.JSONDecodeError as e:
        # If JSON parsing fails, create a basic match result
        print(f"Failed to parse Bedrock response as JSON: {str(e)}")
        print(f"Response text: {response_text[:500]}")
        
        # Fallback: no matches found
        return {
            'matched_po_ids': [],
            'discrepancies': [],
            'confidence_score': 0,
            'reasoning': f"Failed to parse AI response: {str(e)}",
            'line_matches': []
        }


def classify_perfect_match(
    invoice: Dict[str, Any],
    pos: List[Dict[str, Any]],
    matched_po_ids: List[str],
    discrepancies: List[Dict[str, Any]]
) -> bool:
    """
    Classify invoice as perfect match if all line items match within tolerances.
    
    Perfect match criteria:
    - All line items match PO line items within ±5% price tolerance
    - Quantities match exactly
    - Item descriptions match (fuzzy matching)
    - No discrepancies identified by AI
    
    Handles duplicate item descriptions by tracking which PO items have been matched.
    """
    # If AI identified discrepancies, not a perfect match
    if discrepancies and len(discrepancies) > 0:
        return False
    
    # If no POs matched, not a perfect match
    if not matched_po_ids or len(matched_po_ids) == 0:
        return False
    
    # Get matched POs
    matched_pos = [po for po in pos if po.get('POId') in matched_po_ids]
    
    if not matched_pos:
        return False
    
    # Check each invoice line item
    invoice_items = invoice.get('LineItems', [])
    
    # Track which PO items have been matched (to handle duplicates correctly)
    # Key: (po_id, po_item_index), Value: True if matched
    matched_po_items = {}
    
    for inv_item in invoice_items:
        matched = False
        
        # Try to find matching item in any matched PO
        for po in matched_pos:
            po_items = po.get('LineItems', [])
            po_id = po.get('POId')
            
            for po_idx, po_item in enumerate(po_items):
                # Skip if this PO item was already matched
                if matched_po_items.get((po_id, po_idx), False):
                    continue
                
                # Check if descriptions match (fuzzy)
                desc_similarity = string_similarity(
                    inv_item['item_description'].lower(),
                    po_item['ItemDescription'].lower()
                )
                
                if desc_similarity < 0.7:  # 70% similarity threshold
                    continue
                
                # Check quantity match (exact)
                if inv_item['quantity'] != po_item['Quantity']:
                    continue
                
                # Check price match (within ±5% tolerance)
                inv_price = float(inv_item['unit_price'])
                po_price = float(po_item['UnitPrice'])
                price_diff_pct = abs(inv_price - po_price) / po_price if po_price > 0 else 1.0
                
                if price_diff_pct <= PRICE_TOLERANCE + PRICE_TOLERANCE_EPSILON:
                    matched = True
                    # Mark this PO item as matched
                    matched_po_items[(po_id, po_idx)] = True
                    break
            
            if matched:
                break
        
        # If any item didn't match, not a perfect match
        if not matched:
            return False
    
    # All items matched within tolerances
    return True


def string_similarity(str1: str, str2: str) -> float:
    """Calculate similarity between two strings using SequenceMatcher."""
    return SequenceMatcher(None, str1, str2).ratio()


def store_match_results(invoice_id: str, match_result: Dict[str, Any]) -> None:
    """Store match results in DynamoDB Invoices table."""
    try:
        # Convert discrepancies to DynamoDB format
        discrepancies = match_result.get('discrepancies', [])
        
        invoices_table.update_item(
            Key={'InvoiceId': invoice_id},
            UpdateExpression='''
                SET MatchedPOIds = :matched_po_ids,
                    Discrepancies = :discrepancies,
                    AIReasoning = :reasoning,
                    #status = :status
            ''',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={
                ':matched_po_ids': match_result['matched_po_ids'],
                ':discrepancies': discrepancies,
                ':reasoning': match_result['reasoning'],
                ':status': 'MATCHED'
            }
        )
        
        print(f"Stored match results for invoice {invoice_id}")
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ProvisionedThroughputExceededException':
            raise RetryableError(f"DynamoDB throttling: {str(e)}")
        else:
            raise RetryableError(f"Failed to store match results: {str(e)}")


def log_audit_event(action_type: str, entity_id: str, details: Dict[str, Any], reasoning: str) -> None:
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
                'Reasoning': reasoning
            }
        )
    except Exception as e:
        # Don't fail the main operation if audit logging fails
        print(f"Failed to log audit event: {str(e)}")
