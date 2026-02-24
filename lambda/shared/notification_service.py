"""
SNS notification service for sending admin alerts on critical errors.
"""

import os
import json
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize SNS client
sns_client = boto3.client('sns')

# Environment variable for SNS topic ARN
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')


class NotificationService:
    """Service for sending notifications to admins via SNS."""
    
    def __init__(self, topic_arn: Optional[str] = None):
        """
        Initialize notification service.
        
        Args:
            topic_arn: SNS topic ARN (defaults to environment variable)
        """
        self.topic_arn = topic_arn or SNS_TOPIC_ARN
        
        if not self.topic_arn:
            logger.warning("SNS_TOPIC_ARN not configured. Notifications will be logged only.")
    
    def send_notification(
        self,
        subject: str,
        message: str,
        severity: str = 'ERROR',
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send notification to admins.
        
        Args:
            subject: Email subject line
            message: Notification message
            severity: Severity level (INFO, WARNING, ERROR, CRITICAL)
            context: Additional context to include
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.topic_arn:
            logger.warning(f"Cannot send notification (no topic ARN): {subject}")
            return False
        
        try:
            # Build message body
            message_body = self._build_message_body(message, severity, context)
            
            # Send to SNS
            response = sns_client.publish(
                TopicArn=self.topic_arn,
                Subject=f"[ReconcileAI {severity}] {subject}",
                Message=message_body
            )
            
            logger.info(f"Notification sent successfully: {subject} (MessageId: {response['MessageId']})")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to send notification: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending notification: {str(e)}")
            return False
    
    def _build_message_body(
        self,
        message: str,
        severity: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build formatted message body."""
        lines = [
            f"Severity: {severity}",
            f"Timestamp: {self._get_timestamp()}",
            "",
            "Message:",
            message,
        ]
        
        if context:
            lines.extend([
                "",
                "Context:",
                json.dumps(context, indent=2, default=str)
            ])
        
        lines.extend([
            "",
            "---",
            "This is an automated notification from ReconcileAI.",
            "Please review the issue and take appropriate action."
        ])
        
        return "\n".join(lines)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'
    
    def notify_step_function_failure(
        self,
        execution_arn: str,
        error: str,
        invoice_id: Optional[str] = None
    ):
        """
        Notify admins of Step Function execution failure.
        
        Args:
            execution_arn: Step Function execution ARN
            error: Error message
            invoice_id: Invoice ID if available
        """
        subject = "Step Function Execution Failed"
        message = f"A Step Function execution has failed after all retry attempts.\n\nExecution ARN: {execution_arn}\nError: {error}"
        
        context = {
            'execution_arn': execution_arn,
            'error': error
        }
        
        if invoice_id:
            context['invoice_id'] = invoice_id
            message += f"\nInvoice ID: {invoice_id}"
        
        self.send_notification(
            subject=subject,
            message=message,
            severity='CRITICAL',
            context=context
        )
    
    def notify_ai_service_unavailable(
        self,
        duration_minutes: int,
        failed_attempts: int
    ):
        """
        Notify admins of prolonged AI service unavailability.
        
        Args:
            duration_minutes: How long the service has been unavailable
            failed_attempts: Number of failed attempts
        """
        subject = "AI Service Prolonged Unavailability"
        message = (
            f"Amazon Bedrock has been unavailable for {duration_minutes} minutes.\n\n"
            f"Failed attempts: {failed_attempts}\n"
            f"Invoice processing is currently blocked."
        )
        
        self.send_notification(
            subject=subject,
            message=message,
            severity='CRITICAL',
            context={
                'duration_minutes': duration_minutes,
                'failed_attempts': failed_attempts,
                'service': 'Amazon Bedrock'
            }
        )
    
    def notify_dynamodb_access_failure(
        self,
        table_name: str,
        operation: str,
        error: str
    ):
        """
        Notify admins of DynamoDB access failure.
        
        Args:
            table_name: DynamoDB table name
            operation: Operation that failed
            error: Error message
        """
        subject = "DynamoDB Access Failure"
        message = (
            f"Failed to access DynamoDB table after all retry attempts.\n\n"
            f"Table: {table_name}\n"
            f"Operation: {operation}\n"
            f"Error: {error}"
        )
        
        self.send_notification(
            subject=subject,
            message=message,
            severity='CRITICAL',
            context={
                'table_name': table_name,
                'operation': operation,
                'error': error
            }
        )
    
    def notify_pdf_extraction_failure(
        self,
        s3_key: str,
        error: str
    ):
        """
        Notify admins of PDF extraction failure.
        
        Args:
            s3_key: S3 key of the PDF
            error: Error message
        """
        subject = "PDF Extraction Failure"
        message = (
            f"Failed to extract data from PDF.\n\n"
            f"S3 Key: {s3_key}\n"
            f"Error: {error}\n\n"
            f"The invoice has been flagged for manual review."
        )
        
        self.send_notification(
            subject=subject,
            message=message,
            severity='ERROR',
            context={
                's3_key': s3_key,
                'error': error
            }
        )
    
    def notify_high_risk_invoice(
        self,
        invoice_id: str,
        vendor_name: str,
        risk_score: int,
        fraud_flags: List[Dict[str, Any]]
    ):
        """
        Notify admins of high-risk invoice detection.
        
        Args:
            invoice_id: Invoice ID
            vendor_name: Vendor name
            risk_score: Risk score (0-100)
            fraud_flags: List of fraud flags
        """
        subject = f"High-Risk Invoice Detected: {vendor_name}"
        
        flag_descriptions = [f"- {flag.get('description', 'Unknown')}" for flag in fraud_flags]
        flags_text = "\n".join(flag_descriptions)
        
        message = (
            f"A high-risk invoice has been detected and flagged for review.\n\n"
            f"Invoice ID: {invoice_id}\n"
            f"Vendor: {vendor_name}\n"
            f"Risk Score: {risk_score}/100\n\n"
            f"Fraud Flags:\n{flags_text}\n\n"
            f"Please review this invoice in the dashboard."
        )
        
        self.send_notification(
            subject=subject,
            message=message,
            severity='WARNING',
            context={
                'invoice_id': invoice_id,
                'vendor_name': vendor_name,
                'risk_score': risk_score,
                'fraud_flags_count': len(fraud_flags)
            }
        )


# Global notification service instance
_notification_service = None


def get_notification_service() -> NotificationService:
    """Get global notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


def send_critical_error_notification(
    subject: str,
    message: str,
    context: Optional[Dict[str, Any]] = None
):
    """
    Convenience function to send critical error notification.
    
    Args:
        subject: Email subject
        message: Error message
        context: Additional context
    """
    service = get_notification_service()
    service.send_notification(
        subject=subject,
        message=message,
        severity='CRITICAL',
        context=context
    )
