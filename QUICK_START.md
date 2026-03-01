# ReconcileAI - Quick Start Guide

## 🚀 Deploy in 5 Commands

```bash
# 1. Deploy infrastructure (10-15 min)
bash scripts/deploy-full-stack.sh

# 2. Verify deployment (1-2 min)
bash scripts/verify-deployment.sh

# 3. Configure SES email (5 min)
aws ses verify-email-identity --email-address invoices@yourdomain.com
# Click verification link in email
aws ses set-active-receipt-rule-set --rule-set-name ReconcileAI-RuleSet

# 4. Create admin user (2 min)
USER_POOL_ID=$(jq -r '.["ReconcileAI-dev"].UserPoolId' cdk-outputs.json)
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username admin@yourdomain.com \
  --user-attributes Name=email,Value=admin@yourdomain.com Name=email_verified,Value=true \
  --temporary-password TempPassword123! \
  --message-action SUPPRESS

aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username admin@yourdomain.com \
  --group-name Admin

aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username admin@yourdomain.com \
  --password YourSecurePassword123! \
  --permanent

# 5. Test the system (2 min)
bash scripts/test-e2e.sh
```

**Total Time:** ~25-30 minutes

## 📋 What You Get

- ✅ Complete serverless infrastructure on AWS
- ✅ AI-powered invoice matching with Claude 3 Haiku
- ✅ Fraud detection with 4 pattern types
- ✅ Human approval workflow
- ✅ React dashboard with authentication
- ✅ Complete audit trail
- ✅ $0 cost (AWS Free Tier)

## 🎯 Quick Demo

```bash
# Create demo data
bash scripts/create-demo-data.sh

# Start frontend
cd frontend && npm start

# Login at http://localhost:3000
# Username: admin@yourdomain.com
# Password: YourSecurePassword123!
```

## 📊 Architecture

```
Email → SES → S3 → Step Functions → [Extract → Match → Detect → Resolve]
                                         ↓       ↓       ↓        ↓
                                    DynamoDB ← Bedrock AI ← Audit Logs
                                         ↓
                                    API Gateway → React Dashboard
```

## 🔧 Key Commands

### Deployment
```bash
bash scripts/deploy-full-stack.sh    # Deploy everything
bash scripts/verify-deployment.sh    # Verify deployment
cdk deploy                           # Deploy infrastructure only
```

### Testing
```bash
bash scripts/test-e2e.sh             # End-to-end tests
bash scripts/create-demo-data.sh     # Create demo data
cd frontend && npm test              # Frontend tests
```

### Monitoring
```bash
# CloudWatch Logs
aws logs tail /aws/lambda/ReconcileAI-PDFExtraction --follow
aws logs tail /aws/lambda/ReconcileAI-AIMatching --follow

# Step Functions
STATE_MACHINE_ARN=$(jq -r '.["ReconcileAI-dev"].StateMachineArn' cdk-outputs.json)
aws stepfunctions list-executions --state-machine-arn $STATE_MACHINE_ARN

# DynamoDB
aws dynamodb scan --table-name ReconcileAI-Invoices --limit 10
aws dynamodb scan --table-name ReconcileAI-AuditLogs --limit 10
```

### Cleanup
```bash
# Delete all data
aws s3 rm s3://$(jq -r '.["ReconcileAI-dev"].InvoiceBucketName' cdk-outputs.json) --recursive

# Destroy infrastructure
cdk destroy
```

## 📚 Documentation

- `DEPLOYMENT_WALKTHROUGH.md` - Complete deployment guide
- `DEPLOYMENT_CHECKLIST.md` - Step-by-step checklist
- `FINAL_DEPLOYMENT_SUMMARY.md` - What was delivered
- `docs/` - Technical documentation

## 🆘 Troubleshooting

### Deployment fails
```bash
cdk bootstrap --force
rm -rf cdk.out
npm run build
cdk deploy
```

### Frontend can't connect
```bash
# Check API URL
cat frontend/.env

# Verify API Gateway
API_URL=$(jq -r '.["ReconcileAI-dev"].APIGatewayURL' cdk-outputs.json)
echo $API_URL
```

### SES not receiving
```bash
# Verify email
aws ses list-verified-email-addresses

# Check rule set
aws ses describe-active-receipt-rule-set
```

## 💰 AWS Free Tier Limits

| Service | Limit | Status |
|---------|-------|--------|
| Lambda | 1M invocations/month | ✅ |
| DynamoDB | 25GB storage | ✅ |
| S3 | 5GB storage | ✅ |
| Step Functions | 4K transitions/month | ✅ |
| Cognito | 50K MAUs | ✅ |
| SES | 1K emails/month | ✅ |

Monitor usage:
```bash
bash scripts/verify-deployment.sh
```

## 🎓 Demo Scenarios

### 1. Perfect Match (Auto-Approval)
- Upload PO for TechSupplies Inc ($6,250)
- Send matching invoice
- System auto-approves in 60 seconds

### 2. Price Discrepancy (Human Review)
- Upload PO for Office Depot Pro ($7,000)
- Send invoice with 20% price increase
- System flags for human approval

### 3. Fraud Detection
- Send invoice from unknown vendor
- System triggers fraud flag
- Admin receives notification

## 🔗 Quick Links

- **Frontend:** http://localhost:3000 (after `npm start`)
- **API Gateway:** Check `cdk-outputs.json`
- **AWS Console:** https://console.aws.amazon.com
- **CloudWatch Logs:** https://console.aws.amazon.com/cloudwatch/home#logsV2:log-groups

## ✅ Success Checklist

- [ ] Infrastructure deployed
- [ ] All services verified
- [ ] SES configured
- [ ] Admin user created
- [ ] E2E tests pass
- [ ] Frontend loads
- [ ] Demo data created
- [ ] Invoice processing works
- [ ] Audit trail visible

## 🚀 Next Steps

1. **Test locally:** `cd frontend && npm start`
2. **Create demo data:** `bash scripts/create-demo-data.sh`
3. **Deploy to Amplify:** Connect Git repo to AWS Amplify
4. **Monitor usage:** Check AWS Billing Dashboard
5. **Customize:** Add your own fraud detection patterns

---

**Need help?** Check `DEPLOYMENT_WALKTHROUGH.md` for detailed instructions.

**Ready to deploy?** Run `bash scripts/deploy-full-stack.sh` now! 🎉
