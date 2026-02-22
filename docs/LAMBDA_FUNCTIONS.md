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

## 2. AI Matching Lambda

**Function Name**: `ReconcileAI-AIMatching`

### Purpose
Uses Amazon Bedrock Claude 3 Haiku to intelligently match invoice line items against purchase orders, identify discrepancies, and classify perfect matches.

### Specifications
- **Runtime**: Python 3.11
- **Architecture**: ARM64 (Graviton2)
- **Memory**: 512 MB
- **Timeout**: 60 seconds
- **Handler**: `index.lambda_handler`

### Trigger
Invoked by Step Functions workflow after PDF extraction completes.

### Input
```json
{
  "invoice_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Output
Success case:
```json
{
  "statusCode": 200,
  "invoice_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "MATCHING",
  "matched_po_ids": ["PO-123", "PO-456"],
  "discrepancies": [
    {
      "type": "PRICE_MISMATCH",
      "invoice_line": 1,
      "po_line": 1,
      "difference": 5.50,
      "description": "Price difference of $5.50"
    }
  ],
  "is_perfect_match": false,
  "confidence_score": 85
}
```

### Processing Steps

1. **Retrieve Invoice**: Get invoice data from DynamoDB by invoice_id
2. **Query POs**: Find relevant POs by vendor name using VendorNameIndex
3. **Build Prompt**: Create concise prompt with invoice and PO data
4. **Call Bedrock**: Invoke Claude 3 Haiku for AI matching
5. **Parse Response**: Extract matched PO IDs, discrepancies, and reasoning
6. **Classify Match**: Determine if invoice is a perfect match
7. **Store Results**: Update invoice with match results in DynamoDB
8. **Audit**: Log AI decision with reasoning to AuditLogs table

### Perfect Match Classification

An invoice is classified as a perfect match when ALL criteria are met:

1. **No AI Discrepancies**: AI identifies zero discrepancies
2. **PO Match Found**: At least one PO matched
3. **Price Tolerance**: All line items within ±5% of PO prices
4. **Quantity Match**: All quantities match exactly
5. **Description Match**: Item descriptions have ≥70% similarity (fuzzy matching)

### AI Prompt Structure

The function builds a concise prompt to minimize token usage:

```
You are an accounts payable clerk matching an invoice to purchase orders.

INVOICE:
- Number: INV-12345
- Vendor: Acme Corp
- Date: 01/15/2024
- Line Items:
  1. Widget A | Qty: 10 | Unit Price: $25.00 | Total: $250.00
  2. Widget B | Qty: 5 | Unit Price: $50.00 | Total: $250.00
- Total: $500.00

PURCHASE ORDERS:
PO PO-123 (ID: uuid):
  1. Widget A | Qty: 10 | Unit Price: $24.00
  2. Widget B | Qty: 5 | Unit Price: $50.00
Total: $490.00

TASK:
1. Match each invoice line item to PO line items
2. Identify discrepancies (price differences >5%, quantity mismatches, missing items)
3. Calculate confidence score (0-100)
4. Provide step-by-step reasoning

Respond ONLY with valid JSON (no markdown):
{
  "matched_po_ids": ["PO_ID1"],
  "line_matches": [...],
  "overall_confidence": 90,
  "reasoning": "Step-by-step explanation",
  "discrepancies": [...]
}
```

### Cost Optimization

To stay within AWS Free Tier:
- Limits prompt to 5 POs maximum
- Limits each PO to 10 line items
- Sets max_tokens to 2000
- Uses temperature 0.1 for concise responses
- Uses ARM64 architecture for 20% cost savings

### Error Handling

#### Permanent Errors (No Retry)
- Missing invoice_id in event
- Invoice not found in database
- Failed to parse AI response (falls back to no matches)

**Action**: Return success with `status: "FLAGGED"`

#### Retryable Errors
- DynamoDB throttling
- Bedrock API throttling or service unavailability
- Network connectivity issues

**Action**: Raise exception to trigger Step Functions retry

### IAM Permissions

The Lambda function requires:
- **DynamoDB**: `dynamodb:Query` on POs table (VendorNameIndex)
- **DynamoDB**: `dynamodb:GetItem` on Invoices table
- **DynamoDB**: `dynamodb:UpdateItem` on Invoices table
- **DynamoDB**: `dynamodb:PutItem` on AuditLogs table
- **Bedrock**: `bedrock:InvokeModel` for Claude 3 Haiku model

### Environment Variables

- `POS_TABLE_NAME`: DynamoDB table name for POs (e.g., `ReconcileAI-POs`)
- `INVOICES_TABLE_NAME`: DynamoDB table name for invoices (e.g., `ReconcileAI-Invoices`)
- `AUDIT_LOGS_TABLE_NAME`: DynamoDB table name for audit logs (e.g., `ReconcileAI-AuditLogs`)
- `AWS_REGION`: AWS region for Bedrock API calls (e.g., `us-east-1`)

### Dependencies

Packaged with the Lambda function:
- `boto3>=1.28.0`: AWS SDK for Python
- `botocore>=1.31.0`: Low-level AWS SDK

### Monitoring

**CloudWatch Logs**: `/aws/lambda/ReconcileAI-AIMatching`

**Key Metrics**:
- Invocations: Should stay under 1M/month (Free Tier limit)
- Duration: Average ~10-30 seconds per invoice
- Bedrock API calls: Monitor token usage
- Errors: Monitor for Bedrock throttling

**Alarms**:
- Error rate > 5%: Indicates AI service issues
- Duration > 50 seconds: Indicates performance issues
- Bedrock throttling: Indicates Free Tier limit reached

### Audit Trail

Every invocation logs to AuditLogs table:

Success:
```json
{
  "LogId": "uuid",
  "Timestamp": "2024-01-15T10:35:00Z",
  "Actor": "System",
  "ActionType": "InvoiceMatched",
  "EntityType": "Invoice",
  "EntityId": "invoice-uuid",
  "Details": {
    "vendor_name": "Acme Corp",
    "matched_po_ids": ["PO-123"],
    "discrepancies_count": 1,
    "confidence_score": 85,
    "is_perfect_match": false
  },
  "Reasoning": "Matched invoice to PO-123. Line item 1 has price difference of $1.00 (4% variance, within tolerance). Line item 2 matches perfectly."
}
```

### Testing

See `lambda/ai-matching/` for tests.

Run tests:
```bash
cd lambda/ai-matching
python -m pytest -v
```

### Deployment

Deployed automatically via AWS CDK:
```bash
npm run build
cdk deploy
```

---

## Future Lambda Functions

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
