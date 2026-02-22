"""
End-to-End Integration Test for ReconcileAI Backend

This test validates the complete workflow:
1. Upload test PO to DynamoDB
2. Upload test invoice PDF to S3
3. Verify Step Functions execution completes
4. Check invoice status in DynamoDB (auto-approved or flagged)

Requirements tested:
- Email → S3 → Step Functions → DynamoDB workflow
- Perfect match invoice gets auto-approved
- Flagged invoice pauses for approval
"""

import boto3
import json
import time
import uuid
from datetime import datetime
from decimal import Decimal
import os
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

# AWS clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
sfn_client = boto3.client('stepfunctions')

# Table and bucket names (from CDK outputs)
POS_TABLE_NAME = os.environ.get('POS_TABLE_NAME', 'ReconcileAI-POs')
INVOICES_TABLE_NAME = os.environ.get('INVOICES_TABLE_NAME', 'ReconcileAI-Invoices')
AUDIT_LOGS_TABLE_NAME = os.environ.get('AUDIT_LOGS_TABLE_NAME', 'ReconcileAI-AuditLogs')
INVOICE_BUCKET_NAME = os.environ.get('INVOICE_BUCKET_NAME')
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN')

# Get table references
pos_table = dynamodb.Table(POS_TABLE_NAME)
invoices_table = dynamodb.Table(INVOICES_TABLE_NAME)
audit_logs_table = dynamodb.Table(AUDIT_LOGS_TABLE_NAME)


def create_test_po(vendor_name="Acme Corp", po_number="PO-2024-001"):
    """Create a test PO in DynamoDB"""
    po_id = str(uuid.uuid4())
    po_data = {
        'POId': po_id,
        'VendorName': vendor_name,
        'PONumber': po_number,
        'LineItems': [
            {
                'LineNumber': 1,
                'ItemDescription': 'Widget A',
                'Quantity': 10,
                'UnitPrice': Decimal('100.00'),
                'TotalPrice': Decimal('1000.00'),
                'MatchedQuantity': 0
            },
            {
                'LineNumber': 2,
                'ItemDescription': 'Widget B',
                'Quantity': 5,
                'UnitPrice': Decimal('200.00'),
                'TotalPrice': Decimal('1000.00'),
                'MatchedQuantity': 0
            }
        ],
        'TotalAmount': Decimal('2000.00'),
        'UploadDate': datetime.utcnow().isoformat(),
        'UploadedBy': 'test-user',
        'Status': 'Active'
    }
    
    pos_table.put_item(Item=po_data)
    print(f"Created test PO: {po_id} ({po_number})")
    return po_data


def create_perfect_match_invoice_pdf(vendor_name="Acme Corp", invoice_number="INV-2024-001"):
    """Create a PDF invoice that perfectly matches the test PO"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Invoice header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "INVOICE")
    
    c.setFont("Helvetica", 12)
    c.drawString(100, 720, f"Invoice Number: {invoice_number}")
    c.drawString(100, 700, f"Vendor: {vendor_name}")
    c.drawString(100, 680, f"Date: {datetime.utcnow().strftime('%Y-%m-%d')}")
    
    # Line items
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, 640, "Line Items:")
    
    c.setFont("Helvetica", 10)
    y_position = 620
    c.drawString(100, y_position, "Item")
    c.drawString(250, y_position, "Quantity")
    c.drawString(350, y_position, "Unit Price")
    c.drawString(450, y_position, "Total")
    
    y_position -= 20
    c.drawString(100, y_position, "Widget A")
    c.drawString(250, y_position, "10")
    c.drawString(350, y_position, "$100.00")
    c.drawString(450, y_position, "$1,000.00")
    
    y_position -= 20
    c.drawString(100, y_position, "Widget B")
    c.drawString(250, y_position, "5")
    c.drawString(350, y_position, "$200.00")
    c.drawString(450, y_position, "$1,000.00")
    
    # Total
    y_position -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, y_position, "Total Amount:")
    c.drawString(450, y_position, "$2,000.00")
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def create_flagged_invoice_pdf(vendor_name="Suspicious Vendor", invoice_number="INV-2024-999"):
    """Create a PDF invoice that will be flagged (unrecognized vendor)"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Invoice header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "INVOICE")
    
    c.setFont("Helvetica", 12)
    c.drawString(100, 720, f"Invoice Number: {invoice_number}")
    c.drawString(100, 700, f"Vendor: {vendor_name}")
    c.drawString(100, 680, f"Date: {datetime.utcnow().strftime('%Y-%m-%d')}")
    
    # Line items
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, 640, "Line Items:")
    
    c.setFont("Helvetica", 10)
    y_position = 620
    c.drawString(100, y_position, "Suspicious Item")
    c.drawString(250, y_position, "100")
    c.drawString(350, y_position, "$500.00")
    c.drawString(450, y_position, "$50,000.00")
    
    # Total
    y_position -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, y_position, "Total Amount:")
    c.drawString(450, y_position, "$50,000.00")
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def upload_invoice_to_s3(pdf_content, invoice_id):
    """Upload invoice PDF to S3 to trigger Step Functions"""
    s3_key = f"invoices/{datetime.utcnow().year}/{datetime.utcnow().month:02d}/{invoice_id}.pdf"
    
    s3_client.put_object(
        Bucket=INVOICE_BUCKET_NAME,
        Key=s3_key,
        Body=pdf_content,
        ContentType='application/pdf'
    )
    
    print(f"Uploaded invoice to S3: s3://{INVOICE_BUCKET_NAME}/{s3_key}")
    return s3_key


def wait_for_step_function_completion(invoice_id, timeout=120):
    """Wait for Step Functions execution to complete"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # Check invoice status in DynamoDB
        try:
            response = invoices_table.get_item(Key={'InvoiceId': invoice_id})
            if 'Item' in response:
                invoice = response['Item']
                status = invoice.get('Status')
                
                print(f"Invoice status: {status}")
                
                # Check if processing is complete
                if status in ['Approved', 'Rejected', 'Flagged']:
                    return invoice
        except Exception as e:
            print(f"Error checking invoice status: {e}")
        
        time.sleep(5)
    
    raise TimeoutError(f"Step Functions execution did not complete within {timeout} seconds")


def verify_audit_logs(invoice_id):
    """Verify audit logs were created for the invoice"""
    response = audit_logs_table.query(
        IndexName='EntityIdIndex',
        KeyConditionExpression='EntityId = :invoice_id',
        ExpressionAttributeValues={':invoice_id': invoice_id}
    )
    
    logs = response.get('Items', [])
    print(f"Found {len(logs)} audit log entries for invoice {invoice_id}")
    
    # Verify expected log entries exist
    action_types = [log.get('ActionType') for log in logs]
    print(f"Action types logged: {action_types}")
    
    return logs


def cleanup_test_data(po_id, invoice_id, s3_key):
    """Clean up test data after test completes"""
    try:
        # Delete PO
        pos_table.delete_item(Key={'POId': po_id})
        print(f"Deleted test PO: {po_id}")
    except Exception as e:
        print(f"Error deleting PO: {e}")
    
    try:
        # Delete invoice
        invoices_table.delete_item(Key={'InvoiceId': invoice_id})
        print(f"Deleted test invoice: {invoice_id}")
    except Exception as e:
        print(f"Error deleting invoice: {e}")
    
    try:
        # Delete S3 object
        s3_client.delete_object(Bucket=INVOICE_BUCKET_NAME, Key=s3_key)
        print(f"Deleted S3 object: {s3_key}")
    except Exception as e:
        print(f"Error deleting S3 object: {e}")


@pytest.mark.integration
def test_perfect_match_auto_approval():
    """
    Test Case 1: Perfect match invoice gets auto-approved
    
    Validates:
    - Email → S3 → Step Functions → DynamoDB workflow
    - PDF extraction works correctly
    - AI matching identifies perfect match
    - No fraud flags are raised
    - Invoice is automatically approved
    - Audit logs are created
    """
    if not INVOICE_BUCKET_NAME or not STATE_MACHINE_ARN:
        pytest.skip("AWS resources not configured. Set environment variables.")
    
    print("\n" + "="*80)
    print("TEST CASE 1: Perfect Match Auto-Approval")
    print("="*80)
    
    # Step 1: Create test PO
    po_data = create_test_po(vendor_name="Acme Corp", po_number="PO-TEST-001")
    po_id = po_data['POId']
    
    # Step 2: Create perfect match invoice PDF
    invoice_id = str(uuid.uuid4())
    pdf_content = create_perfect_match_invoice_pdf(
        vendor_name="Acme Corp",
        invoice_number="INV-TEST-001"
    )
    
    try:
        # Step 3: Upload invoice to S3 (triggers Step Functions)
        s3_key = upload_invoice_to_s3(pdf_content, invoice_id)
        
        # Step 4: Wait for Step Functions to complete
        print("\nWaiting for Step Functions execution to complete...")
        final_invoice = wait_for_step_function_completion(invoice_id, timeout=120)
        
        # Step 5: Verify invoice was auto-approved
        print("\n" + "-"*80)
        print("VERIFICATION RESULTS:")
        print("-"*80)
        
        assert final_invoice is not None, "Invoice not found in DynamoDB"
        
        status = final_invoice.get('Status')
        print(f"✓ Invoice Status: {status}")
        assert status == 'Approved', f"Expected status 'Approved', got '{status}'"
        
        # Verify no discrepancies
        discrepancies = final_invoice.get('Discrepancies', [])
        print(f"✓ Discrepancies: {len(discrepancies)}")
        assert len(discrepancies) == 0, f"Expected 0 discrepancies, got {len(discrepancies)}"
        
        # Verify no fraud flags
        fraud_flags = final_invoice.get('FraudFlags', [])
        print(f"✓ Fraud Flags: {len(fraud_flags)}")
        assert len(fraud_flags) == 0, f"Expected 0 fraud flags, got {len(fraud_flags)}"
        
        # Verify matched PO
        matched_po_ids = final_invoice.get('MatchedPOIds', [])
        print(f"✓ Matched POs: {matched_po_ids}")
        assert len(matched_po_ids) > 0, "Expected at least one matched PO"
        
        # Verify AI reasoning exists
        ai_reasoning = final_invoice.get('AIReasoning', '')
        print(f"✓ AI Reasoning: {ai_reasoning[:100]}..." if len(ai_reasoning) > 100 else f"✓ AI Reasoning: {ai_reasoning}")
        assert len(ai_reasoning) > 0, "Expected AI reasoning to be present"
        
        # Step 6: Verify audit logs
        print("\n" + "-"*80)
        print("AUDIT LOG VERIFICATION:")
        print("-"*80)
        audit_logs = verify_audit_logs(invoice_id)
        assert len(audit_logs) > 0, "Expected audit logs to be created"
        
        print("\n" + "="*80)
        print("✓ TEST CASE 1 PASSED: Perfect match invoice was auto-approved")
        print("="*80)
        
    finally:
        # Cleanup
        print("\nCleaning up test data...")
        cleanup_test_data(po_id, invoice_id, s3_key)


@pytest.mark.integration
def test_flagged_invoice_pauses_for_approval():
    """
    Test Case 2: Flagged invoice pauses for approval
    
    Validates:
    - Email → S3 → Step Functions → DynamoDB workflow
    - PDF extraction works correctly
    - Fraud detection identifies unrecognized vendor
    - Invoice is flagged for human review
    - Step Functions pauses (does not auto-approve)
    - Audit logs are created
    """
    if not INVOICE_BUCKET_NAME or not STATE_MACHINE_ARN:
        pytest.skip("AWS resources not configured. Set environment variables.")
    
    print("\n" + "="*80)
    print("TEST CASE 2: Flagged Invoice Pauses for Approval")
    print("="*80)
    
    # Step 1: Create flagged invoice PDF (no matching PO)
    invoice_id = str(uuid.uuid4())
    pdf_content = create_flagged_invoice_pdf(
        vendor_name="Suspicious Vendor",
        invoice_number="INV-TEST-999"
    )
    
    try:
        # Step 2: Upload invoice to S3 (triggers Step Functions)
        s3_key = upload_invoice_to_s3(pdf_content, invoice_id)
        
        # Step 3: Wait for Step Functions to complete
        print("\nWaiting for Step Functions execution to complete...")
        final_invoice = wait_for_step_function_completion(invoice_id, timeout=120)
        
        # Step 4: Verify invoice was flagged
        print("\n" + "-"*80)
        print("VERIFICATION RESULTS:")
        print("-"*80)
        
        assert final_invoice is not None, "Invoice not found in DynamoDB"
        
        status = final_invoice.get('Status')
        print(f"✓ Invoice Status: {status}")
        assert status == 'Flagged', f"Expected status 'Flagged', got '{status}'"
        
        # Verify fraud flags exist
        fraud_flags = final_invoice.get('FraudFlags', [])
        print(f"✓ Fraud Flags: {len(fraud_flags)}")
        assert len(fraud_flags) > 0, f"Expected at least 1 fraud flag, got {len(fraud_flags)}"
        
        # Verify unrecognized vendor flag
        flag_types = [flag.get('FlagType') for flag in fraud_flags]
        print(f"✓ Flag Types: {flag_types}")
        assert 'UNRECOGNIZED_VENDOR' in flag_types, "Expected UNRECOGNIZED_VENDOR flag"
        
        # Verify invoice was NOT auto-approved
        print(f"✓ Invoice correctly flagged for human review (not auto-approved)")
        
        # Step 5: Verify audit logs
        print("\n" + "-"*80)
        print("AUDIT LOG VERIFICATION:")
        print("-"*80)
        audit_logs = verify_audit_logs(invoice_id)
        assert len(audit_logs) > 0, "Expected audit logs to be created"
        
        # Verify fraud detection was logged
        fraud_detection_logs = [log for log in audit_logs if log.get('ActionType') == 'FraudDetected']
        print(f"✓ Fraud detection logs: {len(fraud_detection_logs)}")
        assert len(fraud_detection_logs) > 0, "Expected fraud detection to be logged"
        
        print("\n" + "="*80)
        print("✓ TEST CASE 2 PASSED: Flagged invoice paused for approval")
        print("="*80)
        
    finally:
        # Cleanup (no PO to delete in this test)
        print("\nCleaning up test data...")
        cleanup_test_data(None, invoice_id, s3_key)


if __name__ == '__main__':
    """Run integration tests manually"""
    print("ReconcileAI Backend Integration Tests")
    print("="*80)
    print("\nEnsure the following environment variables are set:")
    print("  - INVOICE_BUCKET_NAME")
    print("  - STATE_MACHINE_ARN")
    print("  - AWS credentials configured")
    print("\n" + "="*80)
    
    # Run tests
    try:
        test_perfect_match_auto_approval()
    except Exception as e:
        print(f"\n✗ TEST CASE 1 FAILED: {e}")
    
    try:
        test_flagged_invoice_pauses_for_approval()
    except Exception as e:
        print(f"\n✗ TEST CASE 2 FAILED: {e}")
