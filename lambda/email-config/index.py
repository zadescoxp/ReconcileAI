import json
import boto3
import os
from datetime import datetime
from typing import Dict, Any, List

ses_client = boto3.client('ses')
dynamodb = boto3.resource('dynamodb')

AUDIT_LOGS_TABLE = os.environ.get('AUDIT_LOGS_TABLE_NAME', 'ReconcileAI-AuditLogs')
RULE_SET_NAME = os.environ.get('SES_RULE_SET_NAME', 'ReconcileAI-RuleSet')
S3_BUCKET = os.environ.get('INVOICE_BUCKET_NAME')

audit_table = dynamodb.Table(AUDIT_LOGS_TABLE)


def log_audit(action: str, email: str, user_id: str, status: str, details: Dict = None):
    """Log action to audit table"""
    try:
        log_id = f"email-config-{datetime.utcnow().timestamp()}"
        audit_table.put_item(
            Item={
                'LogId': log_id,
                'Timestamp': datetime.utcnow().isoformat(),
                'EntityId': email,
                'Action': action,
                'UserId': user_id,
                'Status': status,
                'Details': json.dumps(details or {})
            }
        )
    except Exception as e:
        print(f"Failed to log audit: {str(e)}")


def get_cors_headers():
    """Return CORS headers"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,DELETE,OPTIONS'
    }


def lambda_handler(event, context):
    """Handle email configuration requests"""
    print(f"Event: {json.dumps(event)}")
    
    try:
        # Handle OPTIONS for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': ''
            }
        
        # Extract user info from authorizer
        user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub', 'unknown')
        user_email = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('email', 'unknown')
        
        http_method = event.get('httpMethod')
        path = event.get('path', '')
        
        # Route to appropriate handler
        if http_method == 'GET' and '/email-config' in path:
            return handle_list_emails(user_id)
        elif http_method == 'POST' and '/email-config' in path:
            body = json.loads(event.get('body', '{}'))
            return handle_add_email(body, user_id, user_email)
        elif http_method == 'DELETE' and '/email-config' in path:
            body = json.loads(event.get('body', '{}'))
            return handle_remove_email(body, user_id, user_email)
        elif http_method == 'POST' and '/email-config/resend' in path:
            body = json.loads(event.get('body', '{}'))
            return handle_resend_verification(body, user_id, user_email)
        else:
            return {
                'statusCode': 404,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Not found'})
            }
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }


def handle_list_emails(user_id: str):
    """List all verified email identities"""
    try:
        # Get all verified email identities
        response = ses_client.list_identities(IdentityType='EmailAddress')
        identities = response.get('Identities', [])
        
        # Get verification status for each
        if identities:
            verification_response = ses_client.get_identity_verification_attributes(
                Identities=identities
            )
            verification_attrs = verification_response.get('VerificationAttributes', {})
        else:
            verification_attrs = {}
        
        # Format response
        emails = []
        for email in identities:
            attrs = verification_attrs.get(email, {})
            status = attrs.get('VerificationStatus', 'Unknown')
            
            emails.append({
                'email': email,
                'status': 'verified' if status == 'Success' else 'pending' if status == 'Pending' else 'failed',
                'verifiedAt': datetime.utcnow().isoformat() if status == 'Success' else None
            })
        
        log_audit('LIST_EMAILS', 'system', user_id, 'success', {'count': len(emails)})
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({'emails': emails})
        }
        
    except Exception as e:
        print(f"Error listing emails: {str(e)}")
        log_audit('LIST_EMAILS', 'system', user_id, 'failed', {'error': str(e)})
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': f'Failed to list emails: {str(e)}'})
        }


def handle_add_email(body: Dict, user_id: str, user_email: str):
    """Add and verify a new email address"""
    try:
        email = body.get('email')
        if not email:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Email address is required'})
            }
        
        # Verify the email identity in SES
        ses_client.verify_email_identity(EmailAddress=email)
        
        log_audit('ADD_EMAIL', email, user_id, 'success', {'added_by': user_email})
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': f'Verification email sent to {email}',
                'email': email,
                'status': 'pending'
            })
        }
        
    except Exception as e:
        print(f"Error adding email: {str(e)}")
        log_audit('ADD_EMAIL', body.get('email', 'unknown'), user_id, 'failed', {'error': str(e)})
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': f'Failed to add email: {str(e)}'})
        }


def handle_remove_email(body: Dict, user_id: str, user_email: str):
    """Remove an email identity"""
    try:
        email = body.get('email')
        if not email:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Email address is required'})
            }
        
        # Delete the email identity from SES
        ses_client.delete_identity(Identity=email)
        
        log_audit('REMOVE_EMAIL', email, user_id, 'success', {'removed_by': user_email})
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({'message': f'Email {email} removed successfully'})
        }
        
    except Exception as e:
        print(f"Error removing email: {str(e)}")
        log_audit('REMOVE_EMAIL', body.get('email', 'unknown'), user_id, 'failed', {'error': str(e)})
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': f'Failed to remove email: {str(e)}'})
        }


def handle_resend_verification(body: Dict, user_id: str, user_email: str):
    """Resend verification email"""
    try:
        email = body.get('email')
        if not email:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Email address is required'})
            }
        
        # Resend verification by calling verify again
        ses_client.verify_email_identity(EmailAddress=email)
        
        log_audit('RESEND_VERIFICATION', email, user_id, 'success', {'requested_by': user_email})
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({'message': f'Verification email resent to {email}'})
        }
        
    except Exception as e:
        print(f"Error resending verification: {str(e)}")
        log_audit('RESEND_VERIFICATION', body.get('email', 'unknown'), user_id, 'failed', {'error': str(e)})
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': f'Failed to resend verification: {str(e)}'})
        }
