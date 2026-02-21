# Amazon SES Setup Guide

Amazon SES requires manual verification of email addresses or domains before it can receive emails. Follow these steps to configure SES for ReconcileAI.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Access to the email address or domain you want to verify
- ReconcileAI infrastructure deployed (`cdk deploy`)

## Option 1: Verify an Email Address (Quickest for Testing)

### Step 1: Verify Email Address

```bash
aws ses verify-email-identity --email-address invoices@yourdomain.com --region us-east-1
```

### Step 2: Check Verification Email

Check the inbox of the email address you specified. You'll receive a verification email from AWS. Click the verification link.

### Step 3: Confirm Verification Status

```bash
aws ses get-identity-verification-attributes --identities invoices@yourdomain.com --region us-east-1
```

Look for `"VerificationStatus": "Success"` in the output.

### Step 4: Activate the Receipt Rule Set

```bash
aws ses set-active-receipt-rule-set --rule-set-name ReconcileAI-RuleSet --region us-east-1
```

### Step 5: Update Receipt Rule with Recipients

```bash
aws ses update-receipt-rule \
  --rule-set-name ReconcileAI-RuleSet \
  --rule '{
    "Name": "InvoiceReceiptRule",
    "Enabled": true,
    "Recipients": ["invoices@yourdomain.com"],
    "Actions": [
      {
        "S3Action": {
          "BucketName": "reconcileai-invoices-YOUR_ACCOUNT_ID",
          "ObjectKeyPrefix": "emails/"
        }
      }
    ],
    "ScanEnabled": true
  }' \
  --region us-east-1
```

Replace `YOUR_ACCOUNT_ID` with your AWS account ID.

## Option 2: Verify a Domain (Recommended for Production)

### Step 1: Verify Domain

```bash
aws ses verify-domain-identity --domain yourdomain.com --region us-east-1
```

### Step 2: Add DNS Records

The command will return a verification token. Add a TXT record to your domain's DNS:

```
Name: _amazonses.yourdomain.com
Type: TXT
Value: [verification-token-from-step-1]
```

### Step 3: Configure MX Record

Add an MX record to route emails to SES:

```
Name: yourdomain.com (or subdomain.yourdomain.com)
Type: MX
Priority: 10
Value: inbound-smtp.us-east-1.amazonaws.com
```

### Step 4: Wait for DNS Propagation

DNS changes can take up to 72 hours to propagate, but usually complete within a few hours.

### Step 5: Confirm Verification

```bash
aws ses get-identity-verification-attributes --identities yourdomain.com --region us-east-1
```

### Step 6: Activate Rule Set and Update Recipients

Follow steps 4-5 from Option 1, using your domain email addresses.

## Testing Email Reception

### Send a Test Email

Send an email with a PDF attachment to your verified email address:

```
To: invoices@yourdomain.com
Subject: Test Invoice
Body: This is a test invoice email
Attachment: test-invoice.pdf
```

### Verify Email in S3

Check that the email was saved to S3:

```bash
aws s3 ls s3://reconcileai-invoices-YOUR_ACCOUNT_ID/emails/ --recursive
```

You should see the email file stored in the bucket.

## Troubleshooting

### Email Not Received

1. **Check SES Sandbox Status**: By default, SES is in sandbox mode. You can only send/receive emails to verified addresses.
   ```bash
   aws ses get-account-sending-enabled --region us-east-1
   ```

2. **Request Production Access**: To receive emails from any address, request production access:
   - Go to AWS Console → SES → Account Dashboard
   - Click "Request production access"
   - Fill out the form explaining your use case

3. **Check Rule Set Status**:
   ```bash
   aws ses describe-active-receipt-rule-set --region us-east-1
   ```

4. **Verify S3 Permissions**: Ensure SES has permission to write to your S3 bucket (this is configured in the CDK stack).

### DNS Issues

- Use `dig` or `nslookup` to verify DNS records:
  ```bash
  dig TXT _amazonses.yourdomain.com
  dig MX yourdomain.com
  ```

### Rule Set Conflicts

Only one receipt rule set can be active at a time. If you have another active rule set:

```bash
# List all rule sets
aws ses list-receipt-rule-sets --region us-east-1

# Deactivate current rule set
aws ses set-active-receipt-rule-set --region us-east-1
# (no --rule-set-name parameter deactivates all)

# Activate ReconcileAI rule set
aws ses set-active-receipt-rule-set --rule-set-name ReconcileAI-RuleSet --region us-east-1
```

## Next Steps

Once SES is configured and receiving emails:

1. Deploy the PDF extraction Lambda function (Task 2)
2. Configure S3 event notifications to trigger the Step Functions workflow
3. Test end-to-end invoice processing

## AWS Free Tier Limits

- **Email Receiving**: 1,000 emails/month free
- **Email Sending**: 62,000 emails/month free (if needed for notifications)

Monitor your usage in the AWS Console to stay within limits.
