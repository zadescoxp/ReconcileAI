#!/usr/bin/env python3
"""
Check Cognito User Pool custom attributes
Note: Custom attributes cannot be added after pool creation via API
This script checks if the attribute exists
"""

import boto3
from botocore.exceptions import ClientError

USER_POOL_ID = "us-east-1_hhL58Toj6"

def check_user_pool_schema():
    """Check User Pool schema for custom attributes"""
    try:
        client = boto3.client('cognito-idp', region_name='us-east-1')
        
        response = client.describe_user_pool(
            UserPoolId=USER_POOL_ID
        )
        
        schema = response['UserPool']['SchemaAttributes']
        
        print("\n=== User Pool Schema Attributes ===")
        for attr in schema:
            if attr['Name'].startswith('custom:'):
                print(f"✓ {attr['Name']} - {attr.get('AttributeDataType', 'Unknown')}")
        
        # Check if custom:role exists
        role_attr = next((attr for attr in schema if attr['Name'] == 'custom:role'), None)
        
        if not role_attr:
            print("\n⚠️  custom:role attribute does not exist in User Pool schema")
            print("\nNOTE: Custom attributes must be added during User Pool creation")
            print("or via AWS Console. They cannot be added via API after creation.")
            print("\nTo add custom:role attribute:")
            print("1. Go to AWS Console > Cognito > User Pools")
            print(f"2. Select User Pool: {USER_POOL_ID}")
            print("3. Go to 'Sign-up experience' tab")
            print("4. Under 'Custom attributes', add:")
            print("   - Attribute name: role")
            print("   - Type: String")
            print("   - Min length: 1")
            print("   - Max length: 20")
            print("   - Mutable: Yes")
        else:
            print(f"\n✓ custom:role attribute exists in User Pool schema")
        
    except ClientError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_user_pool_schema()
