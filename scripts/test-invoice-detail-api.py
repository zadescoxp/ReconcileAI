#!/usr/bin/env python3
"""
Test the invoice detail API endpoint
"""
import requests
import json
import boto3

# Configuration
API_ENDPOINT = 'https://anr0mybpyb.execute-api.us-east-1.amazonaws.com/prod'
REGION = 'us-east-1'
USER_POOL_ID = 'us-east-1_hhL58Toj6'
CLIENT_ID = '23pakl3uauefnkp2dfglp249gh'
USERNAME = 'admin@reconcileai.com'
PASSWORD = 'Admin123!'

def get_auth_token():
    """Get Cognito auth token"""
    client = boto3.client('cognito-idp', region_name=REGION)
    
    try:
        response = client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': USERNAME,
                'PASSWORD': PASSWORD
            }
        )
        
        id_token = response['AuthenticationResult']['IdToken']
        return id_token
    except Exception as e:
        print(f"Error getting auth token: {e}")
        return None

def get_invoice_ids():
    """Get invoice IDs from DynamoDB"""
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table = dynamodb.Table('ReconcileAI-Invoices')
    
    response = table.scan(Limit=3)
    invoices = response.get('Items', [])
    return [inv['InvoiceId'] for inv in invoices]

def test_invoice_detail(token, invoice_id):
    """Test GET /invoices/{id} endpoint"""
    url = f"{API_ENDPOINT}/invoices/{invoice_id}"
    
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    print(f"\nTesting GET {url}")
    print(f"Headers: Authorization: Bearer {token[:50]}...")
    
    try:
        response = requests.get(url, headers=headers)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print(f"\n✓ SUCCESS! Invoice details retrieved")
            data = response.json()
            print(f"\nResponse structure:")
            print(f"  - invoice: {type(data.get('invoice'))}")
            print(f"  - matchedPOs: {type(data.get('matchedPOs'))} (count: {len(data.get('matchedPOs', []))})")
            print(f"  - auditTrail: {type(data.get('auditTrail'))} (count: {len(data.get('auditTrail', []))})")
            
            if data.get('invoice'):
                inv = data['invoice']
                print(f"\nInvoice details:")
                print(f"  - InvoiceNumber: {inv.get('InvoiceNumber')}")
                print(f"  - VendorName: {inv.get('VendorName')}")
                print(f"  - Status: {inv.get('Status')}")
                print(f"  - TotalAmount: {inv.get('TotalAmount')}")
        else:
            print(f"\n✗ FAILED!")
            print(f"Response Body:")
            try:
                print(json.dumps(response.json(), indent=2))
            except:
                print(response.text)
    except Exception as e:
        print(f"Error: {e}")
        if 'response' in locals():
            print(f"Response text: {response.text}")

if __name__ == '__main__':
    print("Getting auth token...")
    token = get_auth_token()
    
    if not token:
        print("Failed to get auth token")
        exit(1)
    
    print("Getting invoice IDs...")
    invoice_ids = get_invoice_ids()
    
    if not invoice_ids:
        print("No invoices found in database")
        exit(1)
    
    print(f"Found {len(invoice_ids)} invoices")
    
    # Test the first invoice
    print(f"\nTesting invoice detail endpoint for invoice: {invoice_ids[0]}")
    test_invoice_detail(token, invoice_ids[0])
