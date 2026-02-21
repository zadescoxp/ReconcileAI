# AI Matching Lambda Function

## Overview

The AI Matching Lambda function uses Amazon Bedrock Claude 3 Haiku to intelligently match invoice line items against purchase orders. It performs fuzzy matching on item descriptions, validates quantities and prices, and identifies discrepancies.

## Features

- **AI-Powered Matching**: Uses Claude 3 Haiku for intelligent invoice-to-PO matching
- **Perfect Match Classification**: Automatically identifies invoices that match POs within acceptable tolerances
- **Discrepancy Detection**: Identifies price mismatches, quantity differences, and missing items
- **Explainability**: Provides step-by-step reasoning for all matching decisions
- **Cost-Optimized**: Uses ARM architecture and limits token usage to stay within AWS Free Tier

## Input Event

```json
{
  "invoice_id": "uuid-string"
}
```

## Output

```json
{
  "statusCode": 200,
  "invoice_id": "uuid-string",
  "status": "MATCHING",
  "matched_po_ids": ["PO-123"],
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

## Perfect Match Criteria

An invoice is classified as a perfect match when:

1. **Price Tolerance**: All line item prices are within ±5% of PO prices
2. **Quantity Match**: All quantities match exactly
3. **Description Match**: Item descriptions have ≥70% similarity (fuzzy matching)
4. **No Discrepancies**: AI identifies zero discrepancies

## Environment Variables

- `POS_TABLE_NAME`: DynamoDB table name for purchase orders
- `INVOICES_TABLE_NAME`: DynamoDB table name for invoices
- `AUDIT_LOGS_TABLE_NAME`: DynamoDB table name for audit logs
- `AWS_REGION`: AWS region for Bedrock API calls

## IAM Permissions Required

- `dynamodb:Query` on POs table (VendorNameIndex)
- `dynamodb:GetItem` on Invoices table
- `dynamodb:UpdateItem` on Invoices table
- `dynamodb:PutItem` on AuditLogs table
- `bedrock:InvokeModel` for Claude 3 Haiku model

## Error Handling

### Retryable Errors
- DynamoDB throttling
- Bedrock API throttling or service unavailability
- Network connectivity issues

### Permanent Errors
- Missing invoice_id in event
- Invoice not found in database
- Failed to parse AI response (falls back to no matches)

## Cost Optimization

- Uses ARM/Graviton2 architecture for 20% cost savings
- Limits Bedrock prompt to 5 POs and 10 items per PO
- Sets max_tokens to 2000 to control response length
- Uses low temperature (0.1) for consistent, concise responses
- Queries only relevant POs by vendor name

## Audit Logging

All matching operations are logged to the AuditLogs table with:
- Timestamp and actor (System)
- Matched PO IDs and discrepancy count
- Confidence score and perfect match flag
- Full AI reasoning for explainability

## Testing

Run unit tests:
```bash
cd lambda/ai-matching
pytest test_ai_matching_edge_cases.py -v
```

Run property tests:
```bash
pytest test_ai_matching_property.py -v
```

## Deployment

The function is deployed via AWS CDK:
```bash
cd infrastructure
npm run build
cdk deploy
```

## Monitoring

Key CloudWatch metrics to monitor:
- Invocation count (stay under 1M/month for Free Tier)
- Duration (optimize if consistently >30 seconds)
- Error rate (should be <5%)
- Bedrock API throttling errors
