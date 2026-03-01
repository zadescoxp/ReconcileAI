#!/bin/bash

# ReconcileAI Full Stack Deployment Script
# This script deploys the complete ReconcileAI infrastructure and frontend

set -e  # Exit on error

echo "========================================="
echo "ReconcileAI Full Stack Deployment"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI is not installed${NC}"
    echo "Install from: https://aws.amazon.com/cli/"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}ERROR: Node.js is not installed${NC}"
    echo "Install from: https://nodejs.org/"
    exit 1
fi

# Check CDK
if ! command -v cdk &> /dev/null; then
    echo -e "${RED}ERROR: AWS CDK is not installed${NC}"
    echo "Install with: npm install -g aws-cdk"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}ERROR: AWS credentials not configured${NC}"
    echo "Run: aws configure"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites met${NC}"
echo ""

# Get AWS account and region
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)
if [ -z "$AWS_REGION" ]; then
    AWS_REGION="us-east-1"
    echo -e "${YELLOW}No region configured, using default: us-east-1${NC}"
fi

echo "Deploying to:"
echo "  Account: $AWS_ACCOUNT"
echo "  Region: $AWS_REGION"
echo ""

# Step 1: Install backend dependencies
echo "========================================="
echo "Step 1: Installing backend dependencies"
echo "========================================="
npm install
echo -e "${GREEN}✓ Backend dependencies installed${NC}"
echo ""

# Step 2: Build TypeScript
echo "========================================="
echo "Step 2: Building TypeScript code"
echo "========================================="
npm run build
echo -e "${GREEN}✓ TypeScript compiled${NC}"
echo ""

# Step 3: Bootstrap CDK (if needed)
echo "========================================="
echo "Step 3: Checking CDK bootstrap"
echo "========================================="
if ! aws cloudformation describe-stacks --stack-name CDKToolkit --region $AWS_REGION &> /dev/null; then
    echo "CDK not bootstrapped. Bootstrapping now..."
    cdk bootstrap aws://$AWS_ACCOUNT/$AWS_REGION
    echo -e "${GREEN}✓ CDK bootstrapped${NC}"
else
    echo -e "${GREEN}✓ CDK already bootstrapped${NC}"
fi
echo ""

# Step 4: Deploy CDK infrastructure
echo "========================================="
echo "Step 4: Deploying CDK infrastructure"
echo "========================================="
echo "This will create:"
echo "  - DynamoDB tables (POs, Invoices, AuditLogs)"
echo "  - S3 bucket for PDFs"
echo "  - Cognito User Pool"
echo "  - Lambda functions (PDF extraction, AI matching, fraud detection, etc.)"
echo "  - Step Functions workflow"
echo "  - API Gateway"
echo "  - SNS topic for notifications"
echo ""

# Show diff first
echo "Reviewing changes..."
cdk diff

echo ""
read -p "Deploy infrastructure? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 1
fi

cdk deploy --require-approval never --outputs-file cdk-outputs.json

echo -e "${GREEN}✓ Infrastructure deployed${NC}"
echo ""

# Step 5: Extract outputs
echo "========================================="
echo "Step 5: Extracting deployment outputs"
echo "========================================="

if [ ! -f cdk-outputs.json ]; then
    echo -e "${RED}ERROR: cdk-outputs.json not found${NC}"
    exit 1
fi

# Parse outputs (assuming single stack)
STACK_NAME=$(jq -r 'keys[0]' cdk-outputs.json)
USER_POOL_ID=$(jq -r ".[\"$STACK_NAME\"].UserPoolId" cdk-outputs.json)
USER_POOL_CLIENT_ID=$(jq -r ".[\"$STACK_NAME\"].UserPoolClientId" cdk-outputs.json)
API_URL=$(jq -r ".[\"$STACK_NAME\"].APIGatewayURL" cdk-outputs.json)
SNS_TOPIC_ARN=$(jq -r ".[\"$STACK_NAME\"].AdminNotificationTopicArn" cdk-outputs.json)

echo "Deployment outputs:"
echo "  User Pool ID: $USER_POOL_ID"
echo "  User Pool Client ID: $USER_POOL_CLIENT_ID"
echo "  API Gateway URL: $API_URL"
echo "  SNS Topic ARN: $SNS_TOPIC_ARN"
echo ""

# Step 6: Configure frontend environment
echo "========================================="
echo "Step 6: Configuring frontend"
echo "========================================="

cd frontend

# Create .env file
cat > .env << EOF
REACT_APP_USER_POOL_ID=$USER_POOL_ID
REACT_APP_USER_POOL_CLIENT_ID=$USER_POOL_CLIENT_ID
REACT_APP_API_URL=$API_URL
REACT_APP_AWS_REGION=$AWS_REGION
EOF

echo -e "${GREEN}✓ Frontend environment configured${NC}"
echo ""

# Step 7: Install frontend dependencies
echo "Installing frontend dependencies..."
npm install
echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
echo ""

# Step 8: Build frontend
echo "Building frontend..."
npm run build
echo -e "${GREEN}✓ Frontend built${NC}"
echo ""

cd ..

# Step 9: Post-deployment configuration
echo "========================================="
echo "Step 9: Post-deployment configuration"
echo "========================================="
echo ""

echo -e "${YELLOW}IMPORTANT: Manual steps required:${NC}"
echo ""
echo "1. Configure Amazon SES:"
echo "   - Verify your email address or domain"
echo "   - Activate the SES receipt rule set"
echo "   See: docs/SES_SETUP.md"
echo ""
echo "2. Create admin user:"
echo "   aws cognito-idp admin-create-user \\"
echo "     --user-pool-id $USER_POOL_ID \\"
echo "     --username admin@yourdomain.com \\"
echo "     --user-attributes Name=email,Value=admin@yourdomain.com Name=email_verified,Value=true \\"
echo "     --temporary-password TempPassword123! \\"
echo "     --message-action SUPPRESS"
echo ""
echo "   aws cognito-idp admin-add-user-to-group \\"
echo "     --user-pool-id $USER_POOL_ID \\"
echo "     --username admin@yourdomain.com \\"
echo "     --group-name Admin"
echo ""
echo "   aws cognito-idp admin-update-user-attributes \\"
echo "     --user-pool-id $USER_POOL_ID \\"
echo "     --username admin@yourdomain.com \\"
echo "     --user-attributes Name=custom:role,Value=Admin"
echo ""
echo "3. Subscribe to SNS notifications:"
echo "   aws sns subscribe \\"
echo "     --topic-arn $SNS_TOPIC_ARN \\"
echo "     --protocol email \\"
echo "     --notification-endpoint your-admin-email@domain.com"
echo ""
echo "4. Deploy frontend to Amplify (optional):"
echo "   - Connect your Git repository to AWS Amplify"
echo "   - Configure build settings"
echo "   - Deploy"
echo ""

# Save deployment info
cat > deployment-info.txt << EOF
ReconcileAI Deployment Information
===================================

Deployment Date: $(date)
AWS Account: $AWS_ACCOUNT
AWS Region: $AWS_REGION

Infrastructure:
- User Pool ID: $USER_POOL_ID
- User Pool Client ID: $USER_POOL_CLIENT_ID
- API Gateway URL: $API_URL
- SNS Topic ARN: $SNS_TOPIC_ARN

Frontend:
- Build location: frontend/build/
- Environment: frontend/.env

Next Steps:
1. Configure SES (see docs/SES_SETUP.md)
2. Create admin user (see commands above)
3. Subscribe to SNS notifications
4. Deploy frontend to Amplify or serve locally

Local Testing:
- Frontend: cd frontend && npm start
- API: $API_URL
EOF

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Deployment information saved to: deployment-info.txt"
echo ""
echo "To test locally:"
echo "  cd frontend && npm start"
echo ""
echo "API Gateway URL: $API_URL"
echo ""
