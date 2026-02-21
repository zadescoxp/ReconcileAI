# PDF Extraction Lambda Function

This Lambda function extracts text and structured data from invoice PDFs stored in S3.

## Features

- Extracts text from PDF using pdfplumber
- Parses invoice fields: number, vendor, date, line items, total amount
- Stores extracted data in DynamoDB Invoices table
- Logs all operations to AuditLogs table
- Handles errors with retry logic for transient failures

## Architecture

- **Runtime**: Python 3.11 on ARM64 (Graviton2)
- **Memory**: 512 MB
- **Timeout**: 60 seconds
- **Trigger**: Step Functions workflow

## Environment Variables

- `INVOICES_TABLE_NAME`: DynamoDB table for invoices
- `AUDIT_LOGS_TABLE_NAME`: DynamoDB table for audit logs

## Input Event Format

```json
{
  "s3_bucket": "reconcileai-invoices-123456789",
  "s3_key": "invoices/2024/01/invoice.pdf"
}
```

## Output Format

Success:
```json
{
  "statusCode": 200,
  "invoice_id": "uuid",
  "status": "EXTRACTING",
  "vendor_name": "Acme Corp",
  "s3_bucket": "reconcileai-invoices-123456789",
  "s3_key": "invoices/2024/01/invoice.pdf"
}
```

Error (flagged for manual review):
```json
{
  "statusCode": 200,
  "status": "FLAGGED",
  "error": "Missing required invoice fields: invoice_number",
  "flagged_for_manual_review": true
}
```

## Error Handling

### Permanent Errors (No Retry)
- PDF not found in S3
- PDF has no extractable text
- Missing required invoice fields
- Malformed PDF

### Retryable Errors
- S3 service unavailable
- DynamoDB throttling
- Network connectivity issues

## Building and Deployment

### Local Build
```bash
cd lambda/pdf-extraction
chmod +x build.sh
./build.sh
```

### CDK Deployment
The Lambda function is automatically deployed via CDK:
```bash
npm run build
cdk deploy
```

## Dependencies

- `pdfplumber==0.10.3`: PDF text extraction
- `Pillow==10.1.0`: Image processing (required by pdfplumber)
- `pdfminer.six==20221105`: PDF parsing (required by pdfplumber)

## Testing

Run unit tests:
```bash
cd lambda/pdf-extraction
python -m pytest tests/
```

## Monitoring

- CloudWatch Logs: `/aws/lambda/ReconcileAI-PDFExtraction`
- Metrics: Invocations, Duration, Errors, Throttles
- Audit Trail: All operations logged to AuditLogs table
