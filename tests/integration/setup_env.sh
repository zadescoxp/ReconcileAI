#!/bin/bash

# Setup environment variables for integration tests from CDK outputs
# Usage: source setup_env.sh

echo "Fetching CDK stack outputs..."

# Get stack name (adjust if different)
STACK_NAME="ReconcileAIStack"

# Get CDK outputs
OUTPUTS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs' --output json 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "Error: Could not fetch CDK outputs. Ensure the stack is deployed and AWS credentials are configured."
    exit 1
fi

# Extract values from outputs
export INVOICE_BUCKET_NAME=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="InvoiceBucketName") | .OutputValue')
export STATE_MACHINE_ARN=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="StateMachineArn") | .OutputValue')
export POS_TABLE_NAME=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="POsTableName") | .OutputValue')
export INVOICES_TABLE_NAME=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="InvoicesTableName") | .OutputValue')
export AUDIT_LOGS_TABLE_NAME=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="AuditLogsTableName") | .OutputValue')

# Display environment variables
echo ""
echo "Environment variables set:"
echo "  INVOICE_BUCKET_NAME=$INVOICE_BUCKET_NAME"
echo "  STATE_MACHINE_ARN=$STATE_MACHINE_ARN"
echo "  POS_TABLE_NAME=$POS_TABLE_NAME"
echo "  INVOICES_TABLE_NAME=$INVOICES_TABLE_NAME"
echo "  AUDIT_LOGS_TABLE_NAME=$AUDIT_LOGS_TABLE_NAME"
echo ""
echo "You can now run the integration tests:"
echo "  pytest test_e2e_workflow.py -v -s"
