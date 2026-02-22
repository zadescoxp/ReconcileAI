# Setup environment variables for integration tests from CDK outputs (PowerShell)
# Usage: .\setup_env.ps1

Write-Host "Fetching CDK stack outputs..." -ForegroundColor Cyan

# Get stack name (adjust if different)
$STACK_NAME = "ReconcileAIStack"

# Get CDK outputs
try {
    $OUTPUTS = aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs' --output json | ConvertFrom-Json
} catch {
    Write-Host "Error: Could not fetch CDK outputs. Ensure the stack is deployed and AWS credentials are configured." -ForegroundColor Red
    exit 1
}

# Extract values from outputs
$env:INVOICE_BUCKET_NAME = ($OUTPUTS | Where-Object { $_.OutputKey -eq "InvoiceBucketName" }).OutputValue
$env:STATE_MACHINE_ARN = ($OUTPUTS | Where-Object { $_.OutputKey -eq "StateMachineArn" }).OutputValue
$env:POS_TABLE_NAME = ($OUTPUTS | Where-Object { $_.OutputKey -eq "POsTableName" }).OutputValue
$env:INVOICES_TABLE_NAME = ($OUTPUTS | Where-Object { $_.OutputKey -eq "InvoicesTableName" }).OutputValue
$env:AUDIT_LOGS_TABLE_NAME = ($OUTPUTS | Where-Object { $_.OutputKey -eq "AuditLogsTableName" }).OutputValue

# Display environment variables
Write-Host ""
Write-Host "Environment variables set:" -ForegroundColor Green
Write-Host "  INVOICE_BUCKET_NAME=$env:INVOICE_BUCKET_NAME"
Write-Host "  STATE_MACHINE_ARN=$env:STATE_MACHINE_ARN"
Write-Host "  POS_TABLE_NAME=$env:POS_TABLE_NAME"
Write-Host "  INVOICES_TABLE_NAME=$env:INVOICES_TABLE_NAME"
Write-Host "  AUDIT_LOGS_TABLE_NAME=$env:AUDIT_LOGS_TABLE_NAME"
Write-Host ""
Write-Host "You can now run the integration tests:" -ForegroundColor Cyan
Write-Host "  pytest test_e2e_workflow.py -v -s"
