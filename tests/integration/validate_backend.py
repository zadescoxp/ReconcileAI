"""
Backend Validation Script

Validates that all backend components are deployed and accessible before running integration tests.
"""

import boto3
import os
import sys

def check_environment_variables():
    """Check if required environment variables are set"""
    print("Checking environment variables...")
    
    required_vars = [
        'INVOICE_BUCKET_NAME',
        'STATE_MACHINE_ARN',
        'POS_TABLE_NAME',
        'INVOICES_TABLE_NAME',
        'AUDIT_LOGS_TABLE_NAME'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
            print(f"  ✗ {var}: NOT SET")
        else:
            print(f"  ✓ {var}: {value}")
    
    if missing_vars:
        print(f"\nError: Missing environment variables: {', '.join(missing_vars)}")
        print("Run setup_env.ps1 or setup_env.sh to set them automatically.")
        return False
    
    print("✓ All environment variables are set\n")
    return True


def check_dynamodb_tables():
    """Check if DynamoDB tables exist and are accessible"""
    print("Checking DynamoDB tables...")
    
    dynamodb = boto3.client('dynamodb')
    
    tables = [
        os.environ.get('POS_TABLE_NAME'),
        os.environ.get('INVOICES_TABLE_NAME'),
        os.environ.get('AUDIT_LOGS_TABLE_NAME')
    ]
    
    for table_name in tables:
        try:
            response = dynamodb.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']
            print(f"  ✓ {table_name}: {status}")
        except Exception as e:
            print(f"  ✗ {table_name}: ERROR - {e}")
            return False
    
    print("✓ All DynamoDB tables are accessible\n")
    return True


def check_s3_bucket():
    """Check if S3 bucket exists and is accessible"""
    print("Checking S3 bucket...")
    
    s3_client = boto3.client('s3')
    bucket_name = os.environ.get('INVOICE_BUCKET_NAME')
    
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"  ✓ {bucket_name}: Accessible")
    except Exception as e:
        print(f"  ✗ {bucket_name}: ERROR - {e}")
        return False
    
    print("✓ S3 bucket is accessible\n")
    return True


def check_step_functions():
    """Check if Step Functions state machine exists"""
    print("Checking Step Functions state machine...")
    
    sfn_client = boto3.client('stepfunctions')
    state_machine_arn = os.environ.get('STATE_MACHINE_ARN')
    
    try:
        response = sfn_client.describe_state_machine(stateMachineArn=state_machine_arn)
        status = response['status']
        print(f"  ✓ State Machine: {status}")
        print(f"    ARN: {state_machine_arn}")
    except Exception as e:
        print(f"  ✗ State Machine: ERROR - {e}")
        return False
    
    print("✓ Step Functions state machine is accessible\n")
    return True


def check_lambda_functions():
    """Check if Lambda functions exist"""
    print("Checking Lambda functions...")
    
    lambda_client = boto3.client('lambda')
    
    functions = [
        'ReconcileAI-PDFExtraction',
        'ReconcileAI-AIMatching',
        'ReconcileAI-FraudDetection',
        'ReconcileAI-ResolveStep'
    ]
    
    for function_name in functions:
        try:
            response = lambda_client.get_function(FunctionName=function_name)
            state = response['Configuration']['State']
            print(f"  ✓ {function_name}: {state}")
        except Exception as e:
            print(f"  ✗ {function_name}: ERROR - {e}")
            return False
    
    print("✓ All Lambda functions are accessible\n")
    return True


def check_bedrock_access():
    """Check if Bedrock is accessible"""
    print("Checking Bedrock access...")
    
    bedrock_client = boto3.client('bedrock')
    
    try:
        # List foundation models to verify access
        response = bedrock_client.list_foundation_models()
        models = response.get('modelSummaries', [])
        
        # Check if Claude 3 Haiku is available
        haiku_available = any('claude-3-haiku' in model.get('modelId', '') for model in models)
        
        if haiku_available:
            print(f"  ✓ Bedrock accessible with {len(models)} models")
            print(f"  ✓ Claude 3 Haiku is available")
        else:
            print(f"  ⚠ Bedrock accessible but Claude 3 Haiku not found")
            print(f"    Available models: {len(models)}")
    except Exception as e:
        print(f"  ✗ Bedrock: ERROR - {e}")
        print(f"    Note: Bedrock may not be enabled in your region")
        return False
    
    print("✓ Bedrock is accessible\n")
    return True


def main():
    """Run all validation checks"""
    print("="*80)
    print("ReconcileAI Backend Validation")
    print("="*80)
    print()
    
    checks = [
        ("Environment Variables", check_environment_variables),
        ("DynamoDB Tables", check_dynamodb_tables),
        ("S3 Bucket", check_s3_bucket),
        ("Step Functions", check_step_functions),
        ("Lambda Functions", check_lambda_functions),
        ("Bedrock Access", check_bedrock_access)
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"✗ {check_name}: EXCEPTION - {e}\n")
            results.append((check_name, False))
    
    # Summary
    print("="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    
    all_passed = all(result for _, result in results)
    
    for check_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {check_name}")
    
    print("="*80)
    
    if all_passed:
        print("\n✓ All validation checks passed!")
        print("You can now run the integration tests:")
        print("  pytest test_e2e_workflow.py -v -s")
        return 0
    else:
        print("\n✗ Some validation checks failed.")
        print("Please fix the issues before running integration tests.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
