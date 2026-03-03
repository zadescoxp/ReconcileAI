#!/usr/bin/env python3
"""
Verify API Gateway method configuration
"""

import boto3
import json

API_ID = "anr0mybpyb"
REGION = "us-east-1"
RESOURCE_ID = "xmw15q"  # /invoices/{id}

def verify_method():
    """Verify the GET method configuration"""
    print("\n=== Verifying API Gateway Method Configuration ===\n")
    
    api_client = boto3.client('apigateway', region_name=REGION)
    
    try:
        # Get method details
        method = api_client.get_method(
            restApiId=API_ID,
            resourceId=RESOURCE_ID,
            httpMethod='GET'
        )
        
        print("Method Configuration:")
        print(f"  HTTP Method: GET")
        print(f"  Authorization Type: {method.get('authorizationType')}")
        print(f"  Authorizer ID: {method.get('authorizerId')}")
        print(f"  API Key Required: {method.get('apiKeyRequired', False)}")
        
        # Get integration details
        integration = api_client.get_integration(
            restApiId=API_ID,
            resourceId=RESOURCE_ID,
            httpMethod='GET'
        )
        
        print(f"\nIntegration Configuration:")
        print(f"  Type: {integration.get('type')}")
        print(f"  HTTP Method: {integration.get('httpMethod')}")
        print(f"  URI: {integration.get('uri')}")
        
        # Check method response
        try:
            method_response = api_client.get_method_response(
                restApiId=API_ID,
                resourceId=RESOURCE_ID,
                httpMethod='GET',
                statusCode='200'
            )
            print(f"\nMethod Response (200):")
            print(f"  Status Code: 200")
            print(f"  Response Models: {method_response.get('responseModels', {})}")
        except api_client.exceptions.NotFoundException:
            print(f"\n⚠️  Method response not configured, adding it...")
            
            # Add method response
            api_client.put_method_response(
                restApiId=API_ID,
                resourceId=RESOURCE_ID,
                httpMethod='GET',
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Origin': False
                },
                responseModels={
                    'application/json': 'Empty'
                }
            )
            print("✓ Method response added")
            
            # Add integration response
            api_client.put_integration_response(
                restApiId=API_ID,
                resourceId=RESOURCE_ID,
                httpMethod='GET',
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Origin': "'*'"
                }
            )
            print("✓ Integration response added")
            
            # Deploy
            api_client.create_deployment(
                restApiId=API_ID,
                stageName='prod',
                description='Add method responses'
            )
            print("✓ API deployed")
        
        print("\n✅ Method configuration verified")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_method()
