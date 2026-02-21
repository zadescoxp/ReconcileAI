---
inclusion: always
---

# ReconcileAI Product Constraints & Standards

## AWS Free Tier Enforcement (CRITICAL)

All infrastructure MUST stay within AWS Free Tier limits. This is a hard constraint for the competition.

### Allowed Services & Limits

**Compute:**
- AWS Lambda ONLY (ARM/Graviton2 for cost efficiency)
- Stay under 1M free requests/month and 400,000 GB-seconds compute time

**Storage & Database:**
- Amazon S3 (5GB storage, 20,000 GET requests, 2,000 PUT requests/month)
- Amazon DynamoDB On-Demand mode ONLY (25GB storage, 25 WCU, 25 RCU)

**AI/ML:**
- Amazon Bedrock with lightweight models (Claude 3 Haiku preferred for speed/cost)
- Minimize token usage in prompts and responses

**Orchestration:**
- AWS Step Functions (4,000 state transitions/month free)
- Keep state machines concise: MAX 3-4 steps per workflow

**Frontend:**
- React hosted on AWS Amplify (1,000 build minutes/month, 15GB served/month)

**Authentication:**
- Amazon Cognito (50,000 MAUs free)

**Email:**
- Amazon SES (1,000 emails/month free for receiving)

### Forbidden Services

- NO EC2 instances
- NO RDS databases (use DynamoDB instead)
- NO expensive AI models (no Claude Opus, GPT-4, etc.)
- NO NAT Gateways or other costly networking

## Architecture Principles

1. **Serverless-First**: Everything must be event-driven and serverless
2. **Cost-Conscious**: Always choose ARM/Graviton, minimize cold starts, batch operations
3. **Audit Everything**: Every action must be logged to DynamoDB AuditLogs table
4. **Explainable AI**: AI decisions must include step-by-step reasoning
5. **Human-in-the-Loop**: Discrepancies require human approval before proceeding

## Tech Stack (Enforced)

- **Frontend**: React + AWS Amplify
- **Auth**: Amazon Cognito with RBAC (Admin/User roles)
- **Backend**: AWS Lambda (Node.js or Python, ARM architecture)
- **Database**: DynamoDB (On-Demand mode)
- **Storage**: S3 for PDFs
- **AI**: Amazon Bedrock (Claude 3 Haiku)
- **Orchestration**: AWS Step Functions (max 3-4 steps)
- **Email**: Amazon SES for receiving invoices

## Development Standards

- Use Infrastructure as Code (AWS CDK or SAM preferred)
- Implement proper error handling and retries
- Log all operations for audit trail
- Write unit tests for Lambda functions
- Keep Lambda functions small and focused (single responsibility)
- Use environment variables for configuration
