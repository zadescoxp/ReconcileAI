"""
Email Processor Lambda
Processes incoming SES emails, extracts PDF attachments, and saves them to S3
"""

import json
import os
import email
import base64
from email import policy
from email.parser import BytesParser
import boto3
from botocore.exceptions import ClientError

s3_client = boto3.client('s3')
sfn_client = boto3.client('stepfunctions')

INVOICE_BUCKET = os.environ['INVOICE_BUCKET']
STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']


def lambda_handler(event, context):
    """
    Process incoming SES email from S3, extract PDF attachments
    """
    print(f"Event: {json.dumps(event)}")
    
    for record in event.get('Records', []):
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        print(f"Processing email: s3://{bucket}/{key}")
        
        try:
            # Download email from S3
            response = s3_client.get_object(Bucket=bucket, Key=key)
            email_content = response['Body'].read()
            
            # Parse email
            msg = BytesParser(policy=policy.default).parsebytes(email_content)
            
            # Extract sender info
            sender = msg.get('From', 'unknown')
            subject = msg.get('Subject', 'No Subject')
            
            print(f"Email from: {sender}, Subject: {subject}")
            
            # Extract PDF and CSV attachments
            attachment_count = 0
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))
                filename = part.get_filename()
                
                # Check if this is a PDF or CSV attachment
                is_pdf = content_type == 'application/pdf' or (filename and filename.lower().endswith('.pdf'))
                is_csv = content_type == 'text/csv' or (filename and filename.lower().endswith('.csv'))
                
                if (is_pdf or is_csv) and (content_disposition and 'attachment' in content_disposition.lower()):
                    
                    if not filename:
                        filename = f'attachment_{attachment_count}.{"pdf" if is_pdf else "csv"}'
                    
                    attachment_data = part.get_payload(decode=True)
                    
                    if attachment_data:
                        # Save attachment to S3 invoices folder
                        invoice_key = f'invoices/{filename}'
                        s3_client.put_object(
                            Bucket=INVOICE_BUCKET,
                            Key=invoice_key,
                            Body=attachment_data,
                            ContentType=content_type,
                            Metadata={
                                'source': 'email',
                                'sender': sender,
                                'subject': subject,
                                'original_email_key': key
                            }
                        )
                        
                        print(f"Saved attachment: {invoice_key}")
                        
                        # Trigger Step Functions for this invoice
                        execution_input = {
                            's3_bucket': INVOICE_BUCKET,
                            's3_key': invoice_key,
                            'source': 'email',
                            'sender': sender
                        }
                        
                        response = sfn_client.start_execution(
                            stateMachineArn=STATE_MACHINE_ARN,
                            input=json.dumps(execution_input)
                        )
                        
                        print(f"Started Step Functions: {response['executionArn']}")
                        attachment_count += 1
            
            if attachment_count == 0:
                print(f"No PDF or CSV attachments found in email: {key}")
            else:
                print(f"Processed {attachment_count} attachment(s)")
                
        except Exception as e:
            print(f"Error processing email {key}: {str(e)}")
            # Don't raise - we don't want to retry email processing
    
    return {
        'statusCode': 200,
        'body': json.dumps('Email processed successfully')
    }
