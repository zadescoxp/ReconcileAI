#!/usr/bin/env python3
"""
Check Lambda CloudWatch logs for errors
"""

import boto3
from datetime import datetime, timedelta

FUNCTION_NAME = "ReconcileAI-InvoiceManagement"
REGION = "us-east-1"

def check_recent_logs():
    """Check recent Lambda logs"""
    print(f"\n=== Checking Recent Lambda Logs ===\n")
    
    logs_client = boto3.client('logs', region_name=REGION)
    
    log_group_name = f"/aws/lambda/{FUNCTION_NAME}"
    
    try:
        # Get log streams from the last 10 minutes
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=10)
        
        # Get recent log streams
        response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        if not response.get('logStreams'):
            print("No recent log streams found")
            return
        
        print(f"Found {len(response['logStreams'])} recent log streams\n")
        
        # Get events from the most recent stream
        latest_stream = response['logStreams'][0]
        stream_name = latest_stream['logStreamName']
        
        print(f"Reading from stream: {stream_name}\n")
        
        events_response = logs_client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=stream_name,
            startFromHead=False,
            limit=50
        )
        
        events = events_response.get('events', [])
        
        if not events:
            print("No events found in stream")
            return
        
        print(f"Last {len(events)} log events:\n")
        print("=" * 80)
        
        for event in events[-20:]:  # Show last 20 events
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            print(f"[{timestamp}] {message}")
        
        print("=" * 80)
        
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"❌ Log group not found: {log_group_name}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_recent_logs()
