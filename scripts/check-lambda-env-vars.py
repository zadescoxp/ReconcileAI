#!/usr/bin/env python3
"""
Check and update Lambda environment variables
"""

import boto3
import json

FUNCTION_NAME = "ReconcileAI-InvoiceManagement"
REGION = "us-east-1"

def check_and_update_env_vars():
    """Check Lambda environment variables"""
    print(f"\n=== Checking Lambda Environment Variables ===\n")
    
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    try:
        # Get function configuration
        response = lambda_client.get_function_configuration(
            FunctionName=FUNCTION_NAME
        )
        
        env_vars = response.get('Environment', {}).get('Variables', {})
        
        print("Current Environment Variables:")
        for key, value in env_vars.items():
            print(f"  {key}: {value}")
        
        # Check if POS_TABLE_NAME exists
        if 'POS_TABLE_NAME' not in env_vars:
            print("\n⚠️  POS_TABLE_NAME is missing!")
            print("Adding POS_TABLE_NAME...")
            
            env_vars['POS_TABLE_NAME'] = 'ReconcileAI-POs'
            
            lambda_client.update_function_configuration(
                FunctionName=FUNCTION_NAME,
                Environment={
                    'Variables': env_vars
                }
            )
            
            print("✓ POS_TABLE_NAME added")
            print("\nWaiting for Lambda to update...")
            
            # Wait for update to complete
            waiter = lambda_client.get_waiter('function_updated')
            waiter.wait(FunctionName=FUNCTION_NAME)
            
            print("✓ Lambda updated successfully")
        else:
            print(f"\n✓ POS_TABLE_NAME is set to: {env_vars['POS_TABLE_NAME']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_and_update_env_vars()
