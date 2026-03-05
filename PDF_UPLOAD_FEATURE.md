# PDF Upload Support for POs and Invoices

## Overview

Added PDF upload support for Purchase Orders (POs) alongside existing CSV and JSON formats. The system now accepts PDFs and automatically extracts structured data using the existing PDF extraction Lambda.

## What Was Implemented

### Frontend Changes

1. **POUpload Component** (`frontend/src/components/POUpload.tsx`)
   - Updated file type validation to accept `.pdf` files
   - Updated UI text to mention PDF support
   - Added PDF parsing flow

2. **PO Service** (`frontend/src/services/poService.ts`)
   - Added `parsePDFFile()` method
   - Converts PDF to base64 and sends to backend API
   - Added `fileToBase64()` helper method

### Backend Changes

1. **PO Management Lambda** (`lambda/po-management/index.py`)
   - Added `handle_parse_pdf()` endpoint handler
   - Uploads PDF to S3 temporarily
   - Invokes existing PDF extraction Lambda
   - Parses extracted text into PO format
   - Cleans up temporary files
   - Added `parse_po_from_text()` to extract PO data from text

2. **API Gateway**
   - Added `POST /pos/parse-pdf` endpoint
   - Requires Cognito authentication
   - CORS enabled

3. **CDK Infrastructure** (`infrastructure/stacks/reconcile-ai-stack.ts`)
   - Added environment variables to PO Management Lambda:
     - `PDF_EXTRACTION_LAMBDA_NAME`
     - `INVOICE_BUCKET_NAME`
   - Granted permissions:
     - S3 read/write access
     - Lambda invoke permission for PDF extraction

## How It Works

### PO PDF Upload Flow

1. User selects a PDF file in the PO Upload page
2. Frontend converts PDF to base64
3. Frontend calls `POST /pos/parse-pdf` with base64 content
4. Backend Lambda:
   - Decodes base64 to PDF bytes
   - Uploads to S3 temporarily (`temp-pos/` prefix)
   - Invokes PDF extraction Lambda
   - Parses extracted text for PO data:
     - Vendor name (patterns: "Vendor:", "Supplier:", "From:")
     - PO number (patterns: "PO #:", "Purchase Order #:", "Order #:")
     - Line items (description, quantity, unit price)
     - Total amount (calculated from line items)
   - Deletes temporary S3 file
5. Returns structured PO metadata to frontend
6. User reviews and confirms before uploading

### Text Parsing Logic

The system uses regex patterns to extract:
- **PO Number**: Looks for "PO #", "Purchase Order #", "Order #"
- **Vendor Name**: Looks for "Vendor:", "Supplier:", "From:"
- **Line Items**: Identifies lines with 2+ numbers (quantity, price)
- **Descriptions**: Text before the numbers on each line

### Fallback Behavior

- If vendor name not found → defaults to "Unknown Vendor"
- If PO number not found → generates random PO number
- If no line items found → returns empty array (validation will catch this)

## Cost Considerations (AWS Free Tier Compliant)

✅ **No additional AWS costs** - reuses existing infrastructure:
- Uses existing PDF extraction Lambda (pdfplumber library)
- Uses existing S3 bucket
- Uses existing API Gateway
- No Textract or other paid services

## File Type Support Summary

### Purchase Orders (POs)
- ✅ CSV files
- ✅ JSON files  
- ✅ PDF files (NEW)

### Invoices
- ✅ PDF files (via email or direct upload)
- Note: Invoices already supported PDF through the invoice processing workflow

## Testing

To test PDF upload:

1. **Prepare a test PO PDF** with:
   - Vendor name
   - PO number
   - Line items with descriptions, quantities, and prices

2. **Upload via UI**:
   - Go to POs page → Upload tab
   - Drag and drop or click to select PDF
   - Review extracted data
   - Click "Upload PO"

3. **Test via API**:
```bash
# Convert PDF to base64
base64 -i test-po.pdf -o test-po.b64

# Call API
curl -X POST https://185l2o7769.execute-api.us-east-1.amazonaws.com/prod/pos/parse-pdf \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fileName": "test-po.pdf",
    "fileContent": "BASE64_CONTENT_HERE"
  }'
```

## Limitations

1. **PDF Quality**: Extraction quality depends on PDF structure
   - Works best with text-based PDFs
   - Scanned images may have lower accuracy
   - Complex layouts may not parse correctly

2. **Pattern Matching**: Uses regex patterns for data extraction
   - May not work with all PO formats
   - Users can manually edit extracted data before uploading

3. **File Size**: Limited by Lambda payload size (6MB)
   - Large PDFs may fail
   - Consider adding file size validation

## Future Improvements

1. **Enhanced Parsing**: Use AI (Bedrock) for better extraction
2. **Template Learning**: Learn from user corrections
3. **Batch Upload**: Support multiple PDFs at once
4. **Preview**: Show PDF preview alongside extracted data
5. **Confidence Scores**: Indicate extraction confidence per field

## Deployment Status

✅ Backend Lambda updated
✅ API Gateway endpoint added
✅ Frontend component updated
✅ Frontend service updated
✅ Frontend built successfully
✅ Infrastructure deployed

## Next Steps

1. Test with real PO PDFs
2. Gather feedback on extraction accuracy
3. Add similar support for invoice PDFs if needed
4. Consider adding file size limits and validation
