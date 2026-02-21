# ReconcileAI

Autonomous Accounts Payable Clerk - AWS Free Tier Serverless Application

## Overview

ReconcileAI automates invoice processing by:
- Receiving invoices via email (Amazon SES)
- Extracting data from PDFs using AI
- Matching invoices against purchase orders
- Detecting potential fraud
- Routing discrepancies to human approvers

## Architecture

- **Frontend**: React + AWS Amplify
- **Auth**: Amazon Cognito (RBAC)
- **Backend**: AWS Lambda (Python/Node.js, ARM architecture)
- **Database**: DynamoDB (On-Demand mode)
- **Storage**: Amazon S3
- **AI**: Amazon Bedrock (Claude 3 Haiku)
- **Orchestration**: AWS Step Functions
- **Email**: Amazon SES

## Prerequisites

- Node.js 18+ and npm
- AWS CLI configured with credentials
- AWS CDK CLI (`npm install -g aws-cdk`)
- Python 3.11+ (for Lambda functions)

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Bootstrap CDK (first time only)

```bash
cdk bootstrap
```

### 3. Deploy Infrastructure

```bash
npm run build
cdk deploy
```

## Project Structure

```
reconcile-ai/
├── infrastructure/          # CDK infrastructure code
│   ├── app.ts              # CDK app entry point
│   └── stacks/             # CDK stack definitions
├── lambda/                 # Lambda function code
│   ├── extract/            # PDF extraction Lambda
│   ├── match/              # AI matching Lambda
│   ├── detect/             # Fraud detection Lambda
│   └── api/                # API Gateway handlers
├── frontend/               # React dashboard
└── tests/                  # Unit and property tests
```

## AWS Free Tier Compliance

This application is designed to stay within AWS Free Tier limits:
- Lambda: <1M invocations/month, ARM architecture
- DynamoDB: On-Demand mode, <25GB storage
- S3: <5GB storage
- Bedrock: Claude 3 Haiku only
- Step Functions: <4,000 transitions/month

## Development

### Build TypeScript

```bash
npm run build
```

### Watch Mode

```bash
npm run watch
```

### Run Tests

```bash
npm test
```

## Configuration

Environment variables are managed through CDK context in `cdk.json`:
- `reconcileai:environment`: Deployment environment (dev/prod)
- `reconcileai:region`: AWS region (default: us-east-1)

## License

MIT
