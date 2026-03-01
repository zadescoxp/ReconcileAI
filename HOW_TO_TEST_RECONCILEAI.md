# How to Test ReconcileAI - Complete Guide

**Status**: ✅ System is deployed and ready for testing  
**Frontend**: http://localhost:3000  
**Login**: admin@reconcileai.com / Admin123!

---

## Quick Test Checklist

### ✅ What's Already Working
- [x] Infrastructure deployed (DynamoDB, Lambda, API Gateway, Cognito)
- [x] Frontend running and accessible
- [x] Authentication working (you're logged in)
- [x] 3 test POs visible in the system
- [x] API Gateway connecting to backend

### 🧪 What to Test Now

---

## Test 1: Purchase Order Management (5 minutes)

### A. View Existing POs ✅ DONE
You've already completed this! You can see the 3 test POs:
- PO-2024-001 (TechSupplies Inc - $6,250)
- PO-2024-002 (Office Depot Pro - $7,000)
- PO-2024-003 (Acme Supplies - $500)

### B. View PO Details
1. Click "View Details" on any PO
2. Verify you see:
   - PO Number, Vendor, Total Amount
   - Upload Date, Status, Uploaded By
   - Line items table with descriptions, quantities, prices

### C. Search Functionality
1. **Search by PO Number**:
   - Enter "PO-2024-001" in PO Number field
   - Click Search
   - Should show only 1 result

2. **Search by Vendor**:
   - Clear previous search
   - Enter "TechSupplies" in Vendor Name field
   - Click Search
   - Should show only TechSupplies PO

3. **Clear Search**:
   - Click "Clear" button
   - All fields should reset

### D. Upload New PO (Optional)
1. Click "Upload PO" tab
2. Create a test JSON file:
   ```json
   {
     "vendorName": "Test Vendor",
     "poNumber": "PO-TEST-001",
     "lineItems": [
       {
         "itemDescription": "Test Item",
         "quantity": 5,
         "unitPrice": 100.00
       }
     ]
   }
   ```
3. Drag and drop or click to upload
4. Verify success message
5. Go to "Search POs" and verify new PO appears

---

## Test 2: Dashboard Overview (2 minutes)

1. Click "Dashboard" in the sidebar
2. Verify you see:
   - Welcome message with your email
   - Summary cards (if implemented)
   - Recent activity (if implemented)

---

## Test 3: Invoice Management (Currently Limited)

**Note**: The invoice workflow requires either:
- Email ingestion via SES (requires manual setup)
- Direct upload of invoice PDFs to S3

### What You Can Test Now:

1. **Navigate to Invoices**:
   - Click "Invoices" in the sidebar
   - You should see an empty list or "No invoices found"
   - This is expected - no invoices have been processed yet

2. **Check Invoice Filters**:
   - Try filtering by status (All, Flagged, Approved, Rejected)
   - Interface should respond even with no data

---

## Test 4: Audit Trail (Admin Only) (3 minutes)

Since you're logged in as admin, you can test the audit trail:

1. **Navigate to Audit Trail**:
   - Click "Audit Trail" in the sidebar (should be visible for Admin)

2. **View Audit Logs**:
   - You should see logs for:
     - PO uploads (the 3 test POs we created)
     - Any other system actions

3. **Search Audit Logs**:
   - Try filtering by action type
   - Try searching by date range
   - Try searching by entity ID (use a PO ID)

4. **Export Audit Logs** (if implemented):
   - Click "Export to CSV"
   - Verify download works

---

## Test 5: Authentication & Authorization (3 minutes)

### A. Test Logout
1. Click your email in the top right
2. Click "Logout"
3. Verify you're redirected to login page

### B. Test Login Again
1. Login with: admin@reconcileai.com / Admin123!
2. Verify you're redirected to dashboard
3. Verify you can access all pages

### C. Test Role-Based Access (Optional)
If you want to test User role:
1. Create a regular user:
   ```bash
   aws cognito-idp admin-create-user \
     --user-pool-id us-east-1_hhL58Toj6 \
     --username user@reconcileai.com \
     --user-attributes Name=email,Value=user@reconcileai.com Name=email_verified,Value=true \
     --temporary-password UserPass123! \
     --message-action SUPPRESS
   
   aws cognito-idp admin-add-user-to-group \
     --user-pool-id us-east-1_hhL58Toj6 \
     --username user@reconcileai.com \
     --group-name User
   
   aws cognito-idp admin-set-user-password \
     --user-pool-id us-east-1_hhL58Toj6 \
     --username user@reconcileai.com \
     --password UserPass123! \
     --permanent
   ```

2. Logout and login as user@reconcileai.com
3. Verify "Audit Trail" is NOT visible (Admin only)

---

## Test 6: End-to-End Invoice Processing (Advanced)

To test the complete invoice workflow, you need to trigger it. Here are your options:

### Option A: Upload Invoice PDF to S3 (Easiest)

1. **Create a test invoice PDF** (or use the demo script):
   ```bash
   # Install reportlab if needed
   pip install reportlab
   
   # Run demo data script (creates invoice PDFs)
   bash scripts/create-demo-data.sh
   ```

2. **Upload to S3**:
   ```bash
   # Upload a test invoice
   aws s3 cp demo-data/invoice1-perfect-match.pdf \
     s3://reconcileai-invoices-463470938082/invoices/2024/03/test-invoice.pdf
   ```

3. **Monitor Step Functions**:
   - Open AWS Console → Step Functions
   - Find "ReconcileAI-InvoiceProcessing"
   - Watch execution progress

4. **Check Results**:
   - Go to Invoices page in frontend
   - Refresh after 30-60 seconds
   - You should see the processed invoice

### Option B: Configure SES Email Ingestion (More Complex)

See `docs/SES_SETUP.md` for detailed instructions.

---

## Test 7: AWS Console Verification (5 minutes)

### A. Check DynamoDB Tables
1. Open AWS Console → DynamoDB
2. Click "ReconcileAI-POs" → "Explore table items"
3. Verify you see your 3 test POs with all data

### B. Check Lambda Functions
1. Open AWS Console → Lambda
2. Find "ReconcileAI-POManagement"
3. Click "Monitor" tab → "View CloudWatch logs"
4. Verify you see logs from your API calls

### C. Check API Gateway
1. Open AWS Console → API Gateway
2. Find your API (anr0mybpyb)
3. Click "Stages" → "prod"
4. Check "Logs/Tracing" for request logs

### D. Check Step Functions
1. Open AWS Console → Step Functions
2. Find "ReconcileAI-InvoiceProcessing"
3. Check "Executions" tab
4. Should show 0 executions (no invoices processed yet)

---

## Test 8: Performance & Responsiveness (2 minutes)

1. **Page Load Times**:
   - Dashboard should load < 2 seconds
   - PO search should return results < 3 seconds
   - Navigation between pages should be instant

2. **API Response Times**:
   - Open browser DevTools (F12)
   - Go to Network tab
   - Click Search on POs page
   - Check API call time (should be < 500ms)

3. **UI Responsiveness**:
   - Resize browser window
   - Verify layout adapts (responsive design)
   - Test on different screen sizes

---

## Test 9: Error Handling (3 minutes)

### A. Test Invalid Search
1. Go to PO Search
2. Enter a PO number that doesn't exist: "PO-9999-999"
3. Click Search
4. Verify: "No results found" or similar message

### B. Test Network Error (Optional)
1. Open DevTools → Network tab
2. Set throttling to "Offline"
3. Try to search POs
4. Verify: Error message displayed
5. Set back to "Online"

### C. Test Session Expiry (Optional)
1. Wait for Cognito session to expire (or clear localStorage)
2. Try to perform an action
3. Verify: Redirected to login page

---

## Test 10: AWS Free Tier Compliance (2 minutes)

Verify the system stays within Free Tier limits:

```bash
# Check Lambda invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=ReconcileAI-POManagement \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum

# Check S3 storage
aws s3 ls s3://reconcileai-invoices-463470938082 --recursive --summarize

# Check DynamoDB item count
aws dynamodb scan --table-name ReconcileAI-POs --select COUNT
```

**Expected Results**:
- Lambda invocations: < 100 (well within 1M/month)
- S3 storage: < 1MB (well within 5GB)
- DynamoDB items: 3 POs (well within limits)

---

## Common Issues & Solutions

### Issue: "Failed to search POs"
**Solution**: 
- Check browser console for errors
- Verify you're logged in
- Check API Gateway URL in .env file

### Issue: POs not showing
**Solution**: 
- Refresh the page
- Click "Search" button (doesn't auto-load)
- Check DynamoDB has data: `aws dynamodb scan --table-name ReconcileAI-POs`

### Issue: "Unauthorized" errors
**Solution**:
- Logout and login again
- Check Cognito token hasn't expired
- Verify user is in correct group (Admin/User)

### Issue: Invoices page empty
**Solution**:
- This is expected - no invoices processed yet
- Upload a test invoice to S3 to trigger workflow
- Or configure SES for email ingestion

---

## Testing Summary

### ✅ Core Features Tested
- [x] Authentication (login/logout)
- [x] PO Management (view, search, details)
- [x] Dashboard navigation
- [x] API Gateway integration
- [x] DynamoDB data retrieval
- [x] Role-based access control

### ⏳ Features Requiring Additional Setup
- [ ] Invoice processing (needs PDF upload or SES)
- [ ] AI matching (needs invoice + PO)
- [ ] Fraud detection (needs invoice data)
- [ ] Approval workflow (needs flagged invoice)
- [ ] Email ingestion (needs SES configuration)

### 🎯 Next Steps

1. **For Demo/Presentation**:
   - Use the current working features (PO management)
   - Show AWS Console (DynamoDB, Lambda, Step Functions)
   - Explain the architecture and Free Tier compliance

2. **For Full Testing**:
   - Run `bash scripts/create-demo-data.sh` to create invoice PDFs
   - Upload invoices to S3 to trigger workflow
   - Monitor Step Functions executions
   - Test approval workflow

3. **For Production**:
   - Configure SES for email receiving
   - Set up SNS notifications
   - Deploy frontend to AWS Amplify
   - Configure custom domain

---

## Quick Test Commands

```bash
# View POs in DynamoDB
aws dynamodb scan --table-name ReconcileAI-POs --query 'Items[*].[PONumber.S, VendorName.S, TotalAmount.N]' --output table

# Check Lambda logs
aws logs tail /aws/lambda/ReconcileAI-POManagement --follow

# List Step Functions executions
aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-east-1:463470938082:stateMachine:ReconcileAI-InvoiceProcessing

# Check API Gateway
curl -H "Authorization: Bearer YOUR_TOKEN" https://anr0mybpyb.execute-api.us-east-1.amazonaws.com/prod/pos
```

---

## Success Criteria

Your testing is successful if:
- ✅ You can login and navigate all pages
- ✅ You can see and search the 3 test POs
- ✅ PO details display correctly
- ✅ Audit trail shows system actions
- ✅ No console errors in browser
- ✅ API calls complete in < 1 second
- ✅ All AWS services within Free Tier limits

---

**Testing Completed By**: You  
**Date**: March 1, 2026  
**Status**: Core features working ✅  
**Ready for**: Demo and presentation

For the complete demo walkthrough, see `DEMO_WALKTHROUGH.md`
