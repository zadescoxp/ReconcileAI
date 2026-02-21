# Lambda Functions Documentation

This document describes all Lambda functions in the ReconcileAI system.

## Overview

All Lambda functions follow these principles:
- **ARM64 Architecture**: Using Graviton2 for cost efficiency (AWS Free Tier optimization)
- **Error Handling**: Distinguish between retryable and permanent errors
- **Audit Logging**: All operations logged to AuditLogs table
- **Environment Variables**: Configuration via environment variables
- **Timeouts**: Appropriate timeouts based on function complexity

## 1. PDF Extraction Lambda

**Function Name**: `ReconcileAI-PDFExtraction`

### Purpose
Extracts text and structured data from invoice PDFs stored in S3.

### Specifications
- **Runtime**: Python 3.11
- **Architecture**: ARM64 (Graviton2)
- **Memory**: 512 MB
- **Timeout**: 60 seconds
- **Handler**: `index.lambda_handler`

### Trigger
Invoked by Step Functions workflow when a new PDF is uploaded to S3.

### Input
```json
{
  "s3_bucket": "reconcileai-invoices-123456789",
  "s3_key": "invoices/2024/01/invoice-uuid.pdf"
}
```

### Output
Success case:
```json
{
  "statusCode": 200,
  "invoice_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "EXTRACTING",
  "vendor_name": "Acme Corporation",
  "s3_bucket": "reconcileai-invoices-123456789",
  "s3_key": "invoices/2024/01/invoice-uuid.pdf"
}
```

Permanent error case (flagged for manual review):
```json
{
  "statusCode": 200,
  "status": "FLAGGED",
  "error": "Missing required invoice fields: invoice_number, vendor_name",
  "flagged_for_manual_review": true
}
```

### Processing Steps

1. **Download PDF**: Retrieve PDF from S3 using provided bucket and key
2. **Extract Text**: Use pdfplumber to extract text from all pages
3. **Parse Data**: Use regex patterns to identify:
   - Invoice number
   - Vendor name
   - Invoice date
   - Line items (description, quantity, unit price, total)
   - Total amount
4. **Validate**: Ensure all required fields are present
5. **Store**: Save extracted data to DynamoDB Invoices table
6. **Audit**: Log extraction event to AuditLogs table

### Data Extraction Patterns

#### Invoice Number
- `invoice #: INV-12345`
- `invoice number: 2024-001`
- `inv #: ABC123`

#### Vendor Name
- Usually at the top of the invoice
- Patterns: `from: Acme Corp`, `vendor: XYZ Inc`
- Fallback: First capitalized line

#### Invoice Date
- `date: 01/15/2024`
- `invoice date: 2024-01-15`
- Any date pattern: `MM/DD/YYYY` or `DD-MM-YYYY`

#### Line Items
Pattern: `Item Description  Qty  Unit Price  Total`
- Example: `Widget A  10  $25.00  $250.00`
- Extracts: description, quantity, unit price, total price

#### Total Amount
- `total: $1,250.00`
- `amount due: 1250.00`
- `grand total: $1,250.00`

### Error Handling

#### Permanent Errors (No Retry)
These errors indicate the PDF cannot be processed and should be flagged for manual review:
- PDF not found in S3 (NoSuchKey)
- PDF has no pages or no extractable text
- Missing required fields after parsing
- Malformed PDF that cannot be opened

**Action**: Return success with `status: "FLAGGED"` to prevent retries

#### Retryable Errors
These errors are transient and should be retried by Step Functions:
- S3 service unavailable (ServiceUnavailable, SlowDown)
- DynamoDB throttling (ProvisionedThroughputExceededException)
- Network connectivity issues

**Action**: Raise exception to trigger Step Functions retry logic

### IAM Permissions

The Lambda function requires:
- **S3**: `s3:GetObject` on invoice bucket
- **DynamoDB**: `dynamodb:PutItem` on Invoices and AuditLogs tables

### Environment Variables

- `INVOICES_TABLE_NAME`: DynamoDB table name for invoices (e.g., `ReconcileAI-Invoices`)
- `AUDIT_LOGS_TABLE_NAME`: DynamoDB table name for audit logs (e.g., `ReconcileAI-AuditLogs`)

### Dependencies

Packaged with the Lambda function:
- `pdfplumber==0.10.3`: PDF text extraction library
- `Pillow==10.1.0`: Image processing (required by pdfplumber)
- `pdfminer.six==20221105`: PDF parsing engine (required by pdfplumber)

### Monitoring

**CloudWatch Logs**: `/aws/lambda/ReconcileAI-PDFExtraction`

**Key Metrics**:
- Invocations: Should stay under 1M/month (Free Tier limit)
- Duration: Average ~5-15 seconds per invoice
- Errors: Monitor for spikes indicating PDF format issues
- Throttles: Should be zero (indicates Free Tier limit reached)

**Alarms**:
- Error rate > 10%: Indicates PDF format issues or service problems
- Duration > 45 seconds: Indicates large PDFs or performance issues

### Audit Trail

Every invocation logs to AuditLogs table:

Success:
```json
{
  "LogId": "uuid",
  "Timestamp": "2024-01-15T10:30:00Z",
  "Actor": "System",
  "ActionType": "InvoiceExtracted",
  "EntityType": "Invoice",
  "EntityId": "invoice-uuid",
  "Details": {
    "s3_bucket": "reconcileai-invoices-123456789",
    "s3_key": "invoices/2024/01/invoice-uuid.pdf",
    "vendor_name": "Acme Corp",
    "invoice_number": "INV-12345",
    "total_amount": 1250.00,
    "line_items_count": 5
  }
}
```

Error:
```json
{
  "LogId": "uuid",
  "Timestamp": "2024-01-15T10:30:00Z",
  "Actor": "System",
  "ActionType": "ExtractionError",
  "EntityType": "Invoice",
  "EntityId": "s3-key",
  "Details": {
    "error_type": "Permanent",
    "error_message": "Missing required invoice fields: invoice_number",
    "s3_bucket": "reconcileai-invoices-123456789",
    "s3_key": "invoices/2024/01/invoice-uuid.pdf"
  }
}
```

### Testing

See `lambda/pdf-extraction/tests/` for unit tests.

Run tests:
```bash
cd lambda/pdf-extraction
python -m pytest tests/ -v
```

### Deployment

Deployed automatically via AWS CDK:
```bash
npm run build
cdk deploy
```

The CDK stack:
1. Creates the Lambda function with ARM64 architecture
2. Packages the function code and dependencies
3. Grants necessary IAM permissions
4. Sets environment variables
5. Configures CloudWatch logging

---

## Future Lambda Functions

### 2. AI Matching Lambda (Task 3.1)
- **Purpose**: Match invoice line items to PO line items using Amazon Bedrock
- **Runtime**: Python 3.11 ARM64
- **Status**: Not yet implemented

### 3. Fraud Detection Lambda (Task 4.1)
- **Purpose**: Detect fraud patterns in invoices
- **Runtime**: Python 3.11 ARM64
- **Status**: Not yet implemented

### 4. Approval Handler Lambda (Task 10.3)
- **Purpose**: Process human approval/rejection decisions
- **Runtime**: Node.js 20.x ARM64
- **Status**: Not yet implemented

### 5. PO Management Lambda (Task 10.2)
- **Purpose**: Handle PO upload and search operations
- **Runtime**: Node.js 20.x ARM64
- **Status**: Not yet implemented

---

## Best Practices

### 1. ARM64 Architecture
Always use ARM64 (Graviton2) for cost efficiency:
```typescript
architecture: lambda.Architecture.ARM_64
```

### 2. Error Handling Pattern
```python
try:
    # Main logic
    result = process()
    return {'statusCode': 200, 'body': result}
except PermanentError as e:
    # Don't retry - flag for manual review
    log_error(e)
    return {'statusCode': 200, 'status': 'FLAGGED', 'error': str(e)}
except RetryableError as e:
    # Retry via Step Functions
    log_error(e)
    raise
```

### 3. Audit Logging
Always log operations:
```python
log_audit_event(
    action_type="ActionName",
    entity_id="entity-id",
    details={"key": "value"}
)
```

### 4. Environment Variables
Use environment variables for configuration:
```python
TABLE_NAME = os.environ['TABLE_NAME']
```

### 5. Timeouts
Set appropriate timeouts:
- Simple operations: 30 seconds
- PDF processing: 60 seconds
- AI operations: 90 seconds

### 6. Memory Allocation
Optimize for cost:
- Simple operations: 256 MB
- PDF processing: 512 MB
- AI operations: 1024 MB

### 7. Cold Start Optimization
- Keep dependencies minimal
- Use ARM64 for faster cold starts
- Initialize clients outside handler
- Use Lambda layers for shared dependencies
