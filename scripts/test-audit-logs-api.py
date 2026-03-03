#!/usr/bin/env python3
"""
Test script for Audit Logs API endpoint
Tests GET /audit-logs with authentication
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

def test_get_audit_logs():
    """Test GET /audit-logs endpoint"""
    print("\n=== Testing GET /audit-logs ===")
    
    # Get auth token
    token = get_auth_token()
    if not token:
        print("❌ Failed to get authentication token")
        return
    
    print("✓ Got authentication token")
    
    # Test 1: Get all audit logs
    print("\nTest 1: Get all audit logs")
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(f"{API_URL}/audit-logs", headers=headers)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Success! Found {data.get('count', 0)} audit logs")
        if data.get('logs'):
            print(f"\nFirst log:")
            first_log = data['logs'][0]
            print(f"  LogId: {first_log.get('LogId')}")
            print(f"  Timestamp: {first_log.get('Timestamp')}")
            print(f"  Actor: {first_log.get('Actor')}")
            print(f"  ActionType: {first_log.get('ActionType')}")
            print(f"  EntityType: {first_log.get('EntityType')}")
            print(f"  EntityId: {first_log.get('EntityId')}")
    else:
        print(f"❌ Failed: {response.text}")
    
    # Test 2: Filter by action type
    print("\n\nTest 2: Filter by action type (InvoiceReceived)")
    response = requests.get(
        f"{API_URL}/audit-logs?actionType=InvoiceReceived",
        headers=headers
    )
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Success! Found {data.get('count', 0)} logs with action type 'InvoiceReceived'")
    else:
        print(f"❌ Failed: {response.text}")
    
    # Test 3: Filter by actor
    print("\n\nTest 3: Filter by actor (system)")
    response = requests.get(
        f"{API_URL}/audit-logs?actor=system",
        headers=headers
    )
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Success! Found {data.get('count', 0)} logs with actor 'system'")
    else:
        print(f"❌ Failed: {response.text}")

if __name__ == "__main__":
    test_get_audit_logs()
