#!/usr/bin/env python3
"""
Test the invoices API endpoint
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

def test_get_invoices(token):
    """Test GET /invoices endpoint"""
    url = f"{API_ENDPOINT}/invoices"
    
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    print(f"Testing GET {url}")
    print(f"Headers: {headers}")
    
    try:
        response = requests.get(url, headers=headers)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"\nResponse Body:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")

if __name__ == '__main__':
    print("Getting auth token...")
    token = get_auth_token()
    
    if token:
        print(f"Got token: {token[:50]}...")
        print("\nTesting invoices API...\n")
        test_get_invoices(token)
    else:
        print("Failed to get auth token")
        print("\nTrying without auth token...")
        test_get_invoices(None)
