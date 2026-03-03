# Audit Trail Testing Guide

## Issue Fixed
The audit trail page was not accessible because the admin user was missing the `custom:role` attribute in Cognito.

## What Was Done
1. ✅ Verified audit logs API endpoint is working (38 logs found)
2. ✅ Added `custom:role = Admin` attribute to admin@reconcileai.com user
3. ✅ Confirmed custom:role attribute exists in User Pool schema

## Testing Steps

### 1. Restart Frontend (Important!)
The user needs to log out and log back in to get the updated role attribute:

```bash
# If frontend is running, stop it (Ctrl+C)
cd frontend
npm start
```

### 2. Log Out and Log In
1. Go to http://localhost:3000
2. Click "Sign Out" in the top right
3. Log back in with:
   - Email: admin@reconcileai.com
   - Password: Admin123!

### 3. Access Audit Trail
1. Click "Audit Trail" in the sidebar
2. You should now see the audit trail page with logs

### 4. Test Filtering
The audit trail page supports filtering by:
- **Entity ID**: Filter logs for a specific invoice or PO
  - Try: `inv-001`, `inv-002`, `po-001`
- **Actor**: Filter by who performed the action
  - Try: `system`, `admin@reconcileai.com`
- **Action Type**: Filter by type of action
  - Try: `InvoiceReceived`, `FraudDetected`, `InvoiceApproved`
- **Date Range**: Filter by date range

### 5. Test Export
1. Click "Export to CSV" button
2. A CSV file should download with all audit logs

## Current Audit Logs
The system has 38 audit logs including:
- Invoice processing workflows (Received → Extracted → Matched → Approved)
- Fraud detection events
- PO upload events

## API Verification
You can test the API directly:

```bash
python scripts/test-audit-logs-api.py
```

This should show:
- ✓ 38 total audit logs
- ✓ 9 logs with action type 'InvoiceReceived'
- ✓ 26 logs with actor 'system'

## Troubleshooting

### Still Can't Access Audit Trail?
1. Open browser console (F12)
2. Check for any errors
3. Verify the user role is loaded:
   ```javascript
   // In console, check:
   localStorage.getItem('amplify-signin-with-hostedUI')
   ```

### Role Not Updating?
1. Clear browser cache and cookies
2. Log out completely
3. Close all browser tabs
4. Open new browser window
5. Log in again

### API Errors?
Run the test script to verify API is working:
```bash
python scripts/test-audit-logs-api.py
```

## Next Steps
Once audit trail is working, you can:
1. View real-time audit logs for all system actions
2. Filter and search through audit history
3. Export audit logs for compliance reporting
4. Track invoice processing pipeline status
