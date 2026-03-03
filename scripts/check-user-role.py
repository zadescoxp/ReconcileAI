#!/usr/bin/env python3
"""
Check and update user role in Cognito
"""

import boto3
from botocore.exceptions import ClientError

USER_POOL_ID = "us-east-1_hhL58Toj6"
USERNAME = "admin@reconcileai.com"

def check_user_attributes():
    """Check user attributes in Cognito"""
    try:
        client = boto3.client('cognito-idp', region_name='us-east-1')
        
        response = client.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=USERNAME
        )
        
        print(f"\n=== User Attributes for {USERNAME} ===")
        for attr in response['UserAttributes']:
            print(f"{attr['Name']}: {attr['Value']}")
        
        # Check if custom:role exists
        role_attr = next((attr for attr in response['UserAttributes'] if attr['Name'] == 'custom:role'), None)
        
        if not role_attr:
            print("\n⚠️  custom:role attribute is missing!")
            print("Setting custom:role to 'Admin'...")
            
            client.admin_update_user_attributes(
                UserPoolId=USER_POOL_ID,
                Username=USERNAME,
                UserAttributes=[
                    {
                        'Name': 'custom:role',
                        'Value': 'Admin'
                    }
                ]
            )
            print("✓ custom:role set to 'Admin'")
        elif role_attr['Value'] != 'Admin':
            print(f"\n⚠️  custom:role is '{role_attr['Value']}', should be 'Admin'")
            print("Updating custom:role to 'Admin'...")
            
            client.admin_update_user_attributes(
                UserPoolId=USER_POOL_ID,
                Username=USERNAME,
                UserAttributes=[
                    {
                        'Name': 'custom:role',
                        'Value': 'Admin'
                    }
                ]
            )
            print("✓ custom:role updated to 'Admin'")
        else:
            print(f"\n✓ custom:role is correctly set to 'Admin'")
        
    except ClientError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_user_attributes()
