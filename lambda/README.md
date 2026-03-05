# Lambda Functions

This directory contains all AWS Lambda function code for ReconcileAI.

## Structure

Each Lambda function has its own directory with:
- `index.py` - Main Lambda handler code
- `requirements.txt` - Python dependencies (if needed)

## Building Lambda Functions

Lambda functions with Python dependencies need to have those dependencies installed locally before deployment.

### Build a Single Lambda

```bash
./scripts/build-lambda.sh <lambda-name>
```

Example:
```bash
./scripts/build-lambda.sh email-config
```

### Build All Lambdas

```bash
./scripts/build-all-lambdas.sh
```

This will:
1. Create a temporary virtual environment for each Lambda
2. Install dependencies from `requirements.txt`
3. Copy dependencies to the Lambda directory
4. Clean up the virtual environment

## Why Not Commit Dependencies?

Lambda dependencies (boto3, botocore, etc.) are:
- Large (100+ MB per Lambda)
- Platform-specific
- Already available in AWS Lambda runtime (boto3, botocore)
- Gitignored to keep the repository clean

## Deployment

CDK automatically packages Lambda functions with their dependencies when you run:

```bash
cdk deploy
```

The build scripts ensure dependencies are present before deployment.

## Lambda Functions

### Core Processing
- **pdf-extraction** - Extracts text from PDF invoices using pdfplumber
- **ai-matching** - Matches invoices to POs using Amazon Bedrock
- **fraud-detection** - Detects potential fraud in invoices
- **resolve-step** - Auto-approves or flags invoices for review

### API Handlers
- **po-management** - Handles PO upload, search, and PDF parsing
- **invoice-management** - Handles invoice queries and actions
- **audit-logs** - Retrieves audit trail data
- **email-config** - Manages SES email configuration

## Best Practices

1. **Keep functions small** - Single responsibility principle
2. **Use environment variables** - For configuration
3. **Log everything** - For debugging and audit
4. **Handle errors gracefully** - Return proper HTTP status codes
5. **Stay in Free Tier** - Use ARM architecture, minimize memory

## Dependencies

Common dependencies across Lambda functions:
- `boto3` - AWS SDK (usually pre-installed in Lambda runtime)
- `botocore` - Core AWS functionality
- Custom libraries as needed (pdfplumber, etc.)

## Testing Locally

To test a Lambda function locally:

```bash
# Build dependencies first
./scripts/build-lambda.sh <lambda-name>

# Run Python directly
cd lambda/<lambda-name>
python3 -c "from index import lambda_handler; print(lambda_handler({}, {}))"
```

## Troubleshooting

### "Module not found" errors
Run the build script to install dependencies:
```bash
./scripts/build-lambda.sh <lambda-name>
```

### Large deployment packages
- Remove unnecessary dependencies
- Use Lambda layers for shared dependencies
- Ensure .gitignore is excluding dependency folders

### Permission errors
Make sure build scripts are executable:
```bash
chmod +x scripts/*.sh
```
