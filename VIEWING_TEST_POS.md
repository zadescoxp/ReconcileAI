# How to View Test Purchase Orders

## Current Status

✅ **Test POs are in DynamoDB**

I've confirmed that 3 test purchase orders are successfully stored in the ReconcileAI-POs table:

| PO Number | Vendor | Amount |
|-----------|--------|--------|
| PO-2024-001 | TechSupplies Inc | $6,250 |
| PO-2024-002 | Office Depot Pro | $7,000 |
| PO-2024-003 | Acme Supplies | $500 |

## Why You Can't See Them in the Frontend

The frontend requires **authentication** to access the POs. Here's the flow:

```
Frontend → Cognito (login) → Get Token → API Gateway (with token) → Lambda → DynamoDB
```

Without logging in, the frontend can't get the authentication token needed to call the API.

---

## Option 1: View POs via AWS Console (Easiest)

**Steps:**
1. Open AWS Console: https://console.aws.amazon.com/dynamodb
2. Navigate to DynamoDB → Tables
3. Click on **ReconcileAI-POs**
4. Click **Explore table items**
5. You'll see all 3 test POs with full details

**Screenshot locations:**
- POId, PONumber, VendorName, TotalAmount
- LineItems (expand to see details)
- UploadDate, Status

---

## Option 2: View POs via AWS CLI

**Command:**
```bash
aws dynamodb scan --table-name ReconcileAI-POs --output table
```

**Formatted output:**
```bash
aws dynamodb scan --table-name ReconcileAI-POs \
  --query 'Items[*].{PONumber:PONumber.S, Vendor:VendorName.S, Amount:TotalAmount.N, Status:Status.S}' \
  --output table
```

---

## Option 3: View POs in Frontend (Requires Login)

### Step 1: Start Frontend
```bash
cd frontend
npm start
```

The app will open at http://localhost:3000

### Step 2: Login

You need to login with the admin user. However, I notice we need to check if the password is set.

**Check user status:**
```bash
aws cognito-idp admin-get-user \
  --user-pool-id us-east-1_hhL58Toj6 \
  --username admin@reconcileai.com
```

### Step 3: Set/Reset Password (if needed)

If the user doesn't have a permanent password set:

```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_hhL58Toj6 \
  --username admin@reconcileai.com \
  --password "TempPassword123!" \
  --permanent
```

### Step 4: Login to Frontend

1. Open http://localhost:3000
2. Enter credentials:
   - **Email**: admin@reconcileai.com
   - **Password**: TempPassword123!
3. If prompted to change password, set a new one

### Step 5: Navigate to PO Management

1. After login, click **"Purchase Orders"** in the sidebar
2. You should see the 3 test POs listed
3. Click on any PO to view details

---

## Option 4: Test API Directly with Authentication

If you want to test the API without the frontend:

### Step 1: Get Authentication Token

```bash
# Install AWS Amplify CLI if needed
npm install -g @aws-amplify/cli

# Or use AWS CLI to get token (more complex)
```

### Step 2: Call API with Token

```bash
# This requires a valid Cognito ID token
curl -H "Authorization: Bearer <YOUR_TOKEN>" \
  https://anr0mybpyb.execute-api.us-east-1.amazonaws.com/prod/pos
```

---

## Troubleshooting

### Issue: "User not found" or "User not confirmed"

**Solution**: Create a new admin user:

```bash
# Create user
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_hhL58Toj6 \
  --username admin@reconcileai.com \
  --user-attributes Name=email,Value=admin@reconcileai.com Name=email_verified,Value=true \
  --temporary-password "TempPassword123!" \
  --message-action SUPPRESS

# Add to Admin group
aws cognito-idp admin-add-user-to-group \
  --user-pool-id us-east-1_hhL58Toj6 \
  --username admin@reconcileai.com \
  --group-name Admin

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_hhL58Toj6 \
  --username admin@reconcileai.com \
  --password "TempPassword123!" \
  --permanent
```

### Issue: Frontend shows "Network Error" or "401 Unauthorized"

**Possible causes:**
1. Not logged in
2. Token expired (login again)
3. API Gateway authorizer misconfigured
4. CORS issue

**Check API Gateway:**
```bash
aws apigateway get-rest-api --rest-api-id anr0mybpyb
```

### Issue: POs not showing in frontend after login

**Debug steps:**

1. **Check browser console** (F12) for errors
2. **Check Network tab** to see API calls
3. **Verify Lambda function** is working:
   ```bash
   aws lambda invoke \
     --function-name ReconcileAI-POManagement \
     --payload '{"httpMethod":"GET","path":"/pos"}' \
     response.json
   cat response.json
   ```

---

## Quick Verification Script

I'll create a script to verify everything is working:

```bash
#!/bin/bash
echo "=== ReconcileAI PO Verification ==="
echo ""

echo "1. Checking DynamoDB POs..."
aws dynamodb scan --table-name ReconcileAI-POs \
  --query 'Items[*].{PONumber:PONumber.S, Vendor:VendorName.S, Amount:TotalAmount.N}' \
  --output table

echo ""
echo "2. Checking Cognito User..."
aws cognito-idp admin-get-user \
  --user-pool-id us-east-1_hhL58Toj6 \
  --username admin@reconcileai.com \
  --query '{Username:Username, Status:UserStatus, Email:UserAttributes[?Name==`email`].Value|[0]}' \
  --output table

echo ""
echo "3. Checking Lambda Function..."
aws lambda get-function \
  --function-name ReconcileAI-POManagement \
  --query 'Configuration.{Name:FunctionName, Runtime:Runtime, Status:State}' \
  --output table

echo ""
echo "4. Checking API Gateway..."
aws apigateway get-rest-api \
  --rest-api-id anr0mybpyb \
  --query '{Name:name, Id:id}' \
  --output table

echo ""
echo "=== Verification Complete ==="
echo ""
echo "To view POs:"
echo "1. AWS Console: https://console.aws.amazon.com/dynamodb"
echo "2. Frontend: cd frontend && npm start (requires login)"
echo "3. CLI: aws dynamodb scan --table-name ReconcileAI-POs"
```

---

## Summary

**The test POs ARE in DynamoDB** ✅

To see them, you have three options:
1. **AWS Console** (easiest, no login needed)
2. **AWS CLI** (command line, shown above)
3. **Frontend** (requires Cognito login)

The frontend requires authentication because the API Gateway has a Cognito authorizer protecting the endpoints. This is a security feature to ensure only authenticated users can access financial data.

**Recommended**: Use AWS Console to view the POs quickly, or follow the frontend login steps above.
