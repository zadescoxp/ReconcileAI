#!/usr/bin/env python3
"""
Test script for Invoice Detail API endpoint
Tests GET /invoices/{id} with authentication
"""

import requests
import json
import boto3
from botocore.exceptions import ClientError

# Configuration
API_URL = "https://anr0mybpyb.execute-api.us-east-1.amazonaws.com/prod"
USER_POOL_ID = "us-east-1_hhL58Toj6"
CLIENT_ID = "23pakl3uauefnkp2dfglp249gh"
USERNAME = "admin@reconcileai.com"
PASSWORD = "Admin123!"

def get_auth_token():
    """Get Cognito authentication token"""
    try:
        client = boto3.client('cognito-idp', region_name='us-east-1')
        
        response = client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': USERNAME,
                'PASSWORD': PASSWORD
            }
        )
        
        return response['AuthenticationResult']['IdToken']
    except ClientError as e:
        print(f"Error getting auth token: {e}")
        return None

def get_test_invoice_ids():
    """Get invoice IDs from DynamoDB"""
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('ReconcileAI-Invoices')
        
        response = table.scan(Limit=5)
        invoice_ids = [item['InvoiceId'] for item in response.get('Items', [])]
        return invoice_ids
    except Exception as e:
        print(f"Error getting invoice IDs: {e}")
        return []

def test_invoice_detail_endpoint():
    """Test GET /invoices/{id} endpoint"""
    print("\n=== Testing GET /invoices/{id} ===")
    
    # Get auth token
    token = get_auth_token()
    if not token:
        print("❌ Failed to get authentication token")
        return
    
    print("✓ Got authentication token")
    
    # Get test invoice IDs
    invoice_ids = get_test_invoice_ids()
    if not invoice_ids:
        print("❌ No invoices found in database")
        return
    
    print(f"✓ Found {len(invoice_ids)} invoices in database")
    
    # Test with first invoice
    invoice_id = invoice_ids[0]
    print(f"\nTesting with invoice ID: {invoice_id}")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    url = f"{API_URL}/invoices/{invoice_id}"
    print(f"URL: {url}")
    
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✓ Success! Invoice details retrieved")
        print(f"\nInvoice Data:")
        print(json.dumps(data, indent=2, default=str))
    else:
        print(f"\n❌ Failed: {response.text}")
        
        # Try to get more details about the error
        if response.status_code == 403:
            print("\n⚠️  403 Forbidden - This usually means:")
            print("  1. API Gateway method not configured correctly")
            print("  2. Cognito authorizer not attached to the method")
            print("  3. Authorization header format is incorrect")
        elif response.status_code == 404:
            print("\n⚠️  404 Not Found - The endpoint doesn't exist")
            print("  Check if GET method is configured in API Gateway")

if __name__ == "__main__":
    test_invoice_detail_endpoint()
