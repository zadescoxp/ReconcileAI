#!/usr/bin/env python3
"""
Fix Invoice Detail API Gateway endpoint
Manually configure GET method for /invoices/{id}
"""

import boto3
import json

# Configuration
API_ID = "anr0mybpyb"
REGION = "us-east-1"
STAGE_NAME = "prod"

def find_resource_by_path(api_client, api_id, path):
    """Find API Gateway resource by path"""
    try:
        response = api_client.get_resources(restApiId=api_id, limit=500)
        
        for resource in response['items']:
            if resource['path'] == path:
                return resource
        
        return None
    except Exception as e:
        print(f"Error finding resource: {e}")
        return None

def get_cognito_authorizer(api_client, api_id):
    """Get Cognito authorizer ID"""
    try:
        response = api_client.get_authorizers(restApiId=api_id)
        
        for authorizer in response['items']:
            if authorizer['type'] == 'COGNITO_USER_POOLS':
                return authorizer['id']
        
        return None
    except Exception as e:
        print(f"Error getting authorizer: {e}")
        return None

def get_lambda_function_arn(lambda_client, function_name):
    """Get Lambda function ARN"""
    try:
        response = lambda_client.get_function(FunctionName=function_name)
        return response['Configuration']['FunctionArn']
    except Exception as e:
        print(f"Error getting Lambda ARN: {e}")
        return None

def fix_invoice_detail_endpoint():
    """Fix the GET /invoices/{id} endpoint"""
    print("\n=== Fixing Invoice Detail API Gateway Endpoint ===\n")
    
    api_client = boto3.client('apigateway', region_name=REGION)
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    # Step 1: Find the /invoices/{id} resource
    print("Step 1: Finding /invoices/{id} resource...")
    resource = find_resource_by_path(api_client, API_ID, '/invoices/{id}')
    
    if not resource:
        print("❌ Resource /invoices/{id} not found")
        print("   The resource needs to be created in CDK first")
        return
    
    resource_id = resource['id']
    print(f"✓ Found resource: {resource_id}")
    
    # Step 2: Get Cognito authorizer
    print("\nStep 2: Getting Cognito authorizer...")
    authorizer_id = get_cognito_authorizer(api_client, API_ID)
    
    if not authorizer_id:
        print("❌ Cognito authorizer not found")
        return
    
    print(f"✓ Found authorizer: {authorizer_id}")
    
    # Step 3: Get Lambda function ARN
    print("\nStep 3: Getting Lambda function ARN...")
    lambda_arn = get_lambda_function_arn(lambda_client, 'ReconcileAI-InvoiceManagement')
    
    if not lambda_arn:
        print("❌ Lambda function not found")
        return
    
    print(f"✓ Found Lambda: {lambda_arn}")
    
    # Step 4: Check if GET method exists
    print("\nStep 4: Checking if GET method exists...")
    try:
        method = api_client.get_method(
            restApiId=API_ID,
            resourceId=resource_id,
            httpMethod='GET'
        )
        print("✓ GET method already exists")
        print(f"   Authorization Type: {method.get('authorizationType', 'NONE')}")
        
        # Check if it has the correct authorizer
        if method.get('authorizationType') != 'COGNITO_USER_POOLS':
            print("⚠️  Method exists but doesn't use Cognito authorizer")
            print("   Updating method...")
            
            # Update method to use Cognito authorizer
            api_client.update_method(
                restApiId=API_ID,
                resourceId=resource_id,
                httpMethod='GET',
                patchOperations=[
                    {
                        'op': 'replace',
                        'path': '/authorizationType',
                        'value': 'COGNITO_USER_POOLS'
                    },
                    {
                        'op': 'replace',
                        'path': '/authorizerId',
                        'value': authorizer_id
                    }
                ]
            )
            print("✓ Method updated with Cognito authorizer")
        
    except api_client.exceptions.NotFoundException:
        print("⚠️  GET method does not exist, creating it...")
        
        # Create GET method
        api_client.put_method(
            restApiId=API_ID,
            resourceId=resource_id,
            httpMethod='GET',
            authorizationType='COGNITO_USER_POOLS',
            authorizerId=authorizer_id,
            requestParameters={}
        )
        print("✓ GET method created")
        
        # Create method integration
        uri = f"arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
        
        api_client.put_integration(
            restApiId=API_ID,
            resourceId=resource_id,
            httpMethod='GET',
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=uri
        )
        print("✓ Lambda integration created")
        
        # Add Lambda permission
        try:
            # Get AWS account ID
            sts_client = boto3.client('sts', region_name=REGION)
            account_id = sts_client.get_caller_identity()['Account']
            
            lambda_client.add_permission(
                FunctionName='ReconcileAI-InvoiceManagement',
                StatementId=f'apigateway-get-invoice-detail-{resource_id}',
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=f"arn:aws:execute-api:{REGION}:{account_id}:{API_ID}/*/*/*"
            )
            print("✓ Lambda permission added")
        except lambda_client.exceptions.ResourceConflictException:
            print("✓ Lambda permission already exists")
        except Exception as e:
            print(f"⚠️  Lambda permission error (may already exist): {e}")
    
    # Step 5: Deploy the API
    print("\nStep 5: Deploying API to prod stage...")
    try:
        api_client.create_deployment(
            restApiId=API_ID,
            stageName=STAGE_NAME,
            description='Fix invoice detail endpoint'
        )
        print("✓ API deployed successfully")
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return
    
    print("\n✅ Invoice detail endpoint fixed!")
    print(f"\nTest the endpoint:")
    print(f"  python scripts/test-invoice-detail-endpoint.py")

if __name__ == "__main__":
    fix_invoice_detail_endpoint()
