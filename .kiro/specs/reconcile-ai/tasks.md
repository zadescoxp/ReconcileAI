# Implementation Plan: ReconcileAI (1-Week MVP)

## Overview

This is an aggressive 1-week implementation plan focused on delivering a working MVP for the AWS competition. The plan prioritizes core functionality: email ingestion, AI matching, basic fraud detection, and a functional dashboard. Advanced features like comprehensive fraud detection and detailed audit trails will be simplified for the MVP.

**Tech Stack**:
- Backend: Python (Lambda functions, ARM architecture)
- Frontend: TypeScript + React (AWS Amplify)
- Infrastructure: AWS CDK (TypeScript)
- Testing: pytest + hypothesis (Python), jest + fast-check (TypeScript)

**MVP Scope**:
- ✅ Email ingestion via SES → S3
- ✅ PDF text extraction
- ✅ AI matching with Bedrock (Claude 3 Haiku)
- ✅ Basic fraud detection (price spikes, unrecognized vendors)
- ✅ Human approval workflow
- ✅ React dashboard with auth
- ✅ Basic audit logging
- ⚠️ Simplified error handling (basic retries only)
- ⚠️ Minimal UI polish (functional over beautiful)

## Tasks

- [ ] 1. Infrastructure Setup (Day 1)
  - [ ] 1.1 Initialize AWS CDK project and configure AWS account
    - Create CDK app with TypeScript
    - Configure AWS credentials and region
    - Set up CDK context for environment variables
    - _Requirements: 12.1, 12.2_
  
  - [ ] 1.2 Create DynamoDB tables with CDK
    - Define POs table with schema (POId, VendorName, PONumber, LineItems, TotalAmount, UploadDate, UploadedBy)
    - Define Invoices table with schema (InvoiceId, VendorName, InvoiceNumber, LineItems, Status, MatchedPOIds, ReceivedDate, S3Key)
    - Define AuditLogs table with schema (LogId, Timestamp, Actor, ActionType, EntityId, Details)
    - Create GSIs for VendorName and Status queries
    - Configure On-Demand billing mode
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 12.3_
  
  - [ ] 1.3 Create S3 bucket for PDF storage
    - Create bucket with encryption enabled (SSE-S3)
    - Configure bucket policy for Lambda access
    - Set up folder structure (invoices/{year}/{month}/)
    - _Requirements: 12.4, 18.1_
  
  - [ ] 1.4 Set up Amazon Cognito User Pool
    - Create User Pool with email as username
    - Add custom attribute for role (Admin/User)
    - Configure password policy
    - Create Admin and User groups
    - _Requirements: 1.1, 1.2_
  
  - [ ] 1.5 Configure Amazon SES for email receiving
    - Verify domain or email address
    - Create SES receipt rule to save to S3
    - Configure S3 trigger for Lambda
    - _Requirements: 3.1, 14.2_

- [ ] 2. Backend Core - PDF Extraction Lambda (Day 1-2)
  - [ ] 2.1 Create PDF extraction Lambda function
    - Set up Python Lambda with ARM architecture
    - Add pdfplumber dependency via Lambda layer
    - Implement S3 event handler
    - Extract text from PDF using pdfplumber
    - Parse invoice fields (number, vendor, date, line items, total)
    - Store extracted data in DynamoDB Invoices table
    - Log extraction to AuditLogs
    - _Requirements: 4.1, 4.2, 4.4, 10.1_
  
  - [ ]* 2.2 Write property test for PDF extraction
    - **Property 9: Invoice Data Extraction Completeness**
    - **Validates: Requirements 4.1, 4.2, 4.4**
  
  - [ ]* 2.3 Write unit tests for PDF extraction edge cases
    - Test malformed PDFs
    - Test PDFs with no text
    - Test PDFs with missing fields
    - _Requirements: 4.3_

- [ ] 3. Backend Core - AI Matching Lambda (Day 2-3)
  - [ ] 3.1 Create AI matching Lambda function
    - Set up Python Lambda with ARM architecture
    - Implement Bedrock API client for Claude 3 Haiku
    - Query relevant POs from DynamoDB by vendor name
    - Build concise prompt with invoice and PO data
    - Parse Bedrock JSON response for matches and discrepancies
    - Store match results in Invoices table
    - Log AI decision with reasoning to AuditLogs
    - _Requirements: 5.1, 5.2, 5.4, 6.1, 6.2, 10.2_
  
  - [ ] 3.2 Implement perfect match classification logic
    - Check all line items match within ±5% price tolerance
    - Check quantities match exactly
    - Check item descriptions match (fuzzy matching)
    - Set is_perfect_match flag
    - _Requirements: 5.3_
  
  - [ ]* 3.3 Write property test for AI matching
    - **Property 12: Perfect Match Classification**
    - **Validates: Requirements 5.3**
  
  - [ ]* 3.4 Write property test for discrepancy detection
    - **Property 13: Discrepancy Detection Completeness**
    - **Validates: Requirements 5.4**
  
  - [ ]* 3.5 Write unit tests for AI matching edge cases
    - Test invoice with no matching POs
    - Test invoice with multiple matching POs
    - Test Bedrock API failures
    - _Requirements: 5.1, 5.2_

- [ ] 4. Backend Core - Fraud Detection Lambda (Day 3)
  - [ ] 4.1 Create fraud detection Lambda function
    - Set up Python Lambda with ARM architecture
    - Implement price spike detection (>20% above historical average)
    - Implement unrecognized vendor detection (no POs for vendor)
    - Implement duplicate invoice detection (same invoice number + vendor)
    - Implement amount exceedance detection (>10% over PO total)
    - Store fraud flags in Invoices table
    - Log fraud detection to AuditLogs
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 10.1_
  
  - [ ]* 4.2 Write property test for price spike detection
    - **Property 16: Price Spike Detection**
    - **Validates: Requirements 7.1**
  
  - [ ]* 4.3 Write property test for unrecognized vendor detection
    - **Property 17: Unrecognized Vendor Detection**
    - **Validates: Requirements 7.2**
  
  - [ ]* 4.4 Write unit tests for fraud detection edge cases
    - Test invoice with multiple fraud flags
    - Test invoice with no historical data
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 5. Step Functions Workflow (Day 3-4)
  - [ ] 5.1 Define Step Functions state machine with CDK
    - Create 4-step workflow: Extract → Match → Detect → Resolve
    - Configure retry logic (3 retries with exponential backoff)
    - Configure error handling (catch and flag for manual review)
    - Add S3 trigger to start execution on PDF upload
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_
  
  - [ ] 5.2 Implement auto-approval logic in Resolve step
    - Check if invoice has zero discrepancies and zero fraud flags
    - If clean, update status to "Approved" and complete workflow
    - If flagged, update status to "Flagged" and pause for human approval
    - Log approval decision to AuditLogs
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 7.5_
  
  - [ ]* 5.3 Write property test for auto-approval
    - **Property 25: Auto-Approval for Clean Invoices**
    - **Validates: Requirements 9.1**
  
  - [ ]* 5.4 Write property test for workflow pause on flags
    - **Property 20: Workflow Pause on Flags**
    - **Validates: Requirements 7.5, 8.1**

- [ ] 6. Checkpoint - Backend Integration Test
  - Run end-to-end test: email → S3 → Step Functions → DynamoDB
  - Verify perfect match invoice gets auto-approved
  - Verify flagged invoice pauses for approval
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Frontend - Authentication & Layout (Day 4-5)
  - [ ] 7.1 Initialize React app with AWS Amplify
    - Create React app with TypeScript
    - Install Amplify libraries (@aws-amplify/ui-react, aws-amplify)
    - Configure Amplify with Cognito User Pool
    - Set up Amplify hosting
    - _Requirements: 13.1, 1.1_
  
  - [ ] 7.2 Implement authentication UI
    - Create login page with Amplify Authenticator component
    - Implement role-based routing (Admin vs User)
    - Add logout functionality
    - Store user session and role in context
    - _Requirements: 1.3, 1.4, 1.5_
  
  - [ ] 7.3 Create main dashboard layout
    - Create navigation bar with user info and logout
    - Create sidebar with menu items (Dashboard, POs, Invoices, Audit Trail)
    - Create responsive layout with React Router
    - _Requirements: 13.2_

- [ ] 8. Frontend - PO Management (Day 5)
  - [ ] 8.1 Create PO upload component
    - Build file upload UI with drag-and-drop
    - Parse uploaded CSV/JSON file for PO data
    - Validate PO has required fields
    - Call API Gateway → Lambda to store PO in DynamoDB
    - Display success/error messages
    - _Requirements: 2.1, 2.2, 13.3_
  
  - [ ] 8.2 Create PO search and list component
    - Build search form (PO number, vendor name, date range)
    - Call API Gateway → Lambda to query DynamoDB
    - Display PO list in table with pagination
    - Add click to view PO details
    - _Requirements: 2.4, 13.4_
  
  - [ ]* 8.3 Write property test for PO validation
    - **Property 2: PO Validation Completeness**
    - **Validates: Requirements 2.1**
  
  - [ ]* 8.4 Write unit tests for PO upload component
    - Test file upload with valid PO
    - Test file upload with invalid PO
    - Test API error handling
    - _Requirements: 2.1, 2.2_

- [ ] 9. Frontend - Invoice Review & Approval (Day 5-6)
  - [ ] 9.1 Create invoice list component
    - Call API Gateway → Lambda to query Invoices table
    - Display invoices in table with status badges
    - Filter by status (All, Flagged, Approved, Rejected)
    - Add click to view invoice details
    - _Requirements: 13.2, 13.5_
  
  - [ ] 9.2 Create invoice detail component
    - Display invoice data (number, vendor, date, line items, total)
    - Display matched PO data side-by-side
    - Display discrepancies with highlighting
    - Display fraud flags with severity indicators
    - Display AI reasoning in expandable section
    - _Requirements: 8.3, 13.6_
  
  - [ ] 9.3 Implement approval actions
    - Add Approve and Reject buttons for flagged invoices
    - Add comment/reason text input
    - Call API Gateway → Lambda to update invoice status
    - Resume Step Functions execution via API
    - Display success/error messages
    - _Requirements: 8.4, 8.5, 8.6_
  
  - [ ]* 9.4 Write unit tests for invoice approval component
    - Test approve action
    - Test reject action
    - Test API error handling
    - _Requirements: 8.5, 8.6_

- [ ] 10. API Gateway & Lambda Handlers (Day 6)
  - [ ] 10.1 Create API Gateway REST API with CDK
    - Define API with Cognito authorizer
    - Create endpoints: POST /pos, GET /pos, GET /invoices, POST /invoices/{id}/approve, POST /invoices/{id}/reject
    - Configure CORS for frontend domain
    - _Requirements: 18.4, 18.6_
  
  - [ ] 10.2 Create PO management Lambda handlers
    - Implement POST /pos handler (validate and store PO)
    - Implement GET /pos handler (search and retrieve POs)
    - Add input sanitization for all user inputs
    - _Requirements: 2.1, 2.2, 2.4, 18.5_
  
  - [ ] 10.3 Create invoice management Lambda handlers
    - Implement GET /invoices handler (query with filters)
    - Implement POST /invoices/{id}/approve handler (update status, resume Step Function)
    - Implement POST /invoices/{id}/reject handler (update status, halt Step Function)
    - Add input sanitization for all user inputs
    - Log all actions to AuditLogs
    - _Requirements: 8.5, 8.6, 10.3, 18.5_
  
  - [ ]* 10.4 Write property test for input sanitization
    - **Property 42: Input Sanitization**
    - **Validates: Requirements 18.5**

- [ ] 11. Audit Trail & Monitoring (Day 6-7)
  - [ ] 11.1 Create audit trail component (Admin only)
    - Build search form (entity ID, actor, action type, date range)
    - Call API Gateway → Lambda to query AuditLogs table
    - Display audit logs in table with expandable details
    - Add export to CSV functionality
    - _Requirements: 10.6, 13.7_
  
  - [ ] 11.2 Implement comprehensive audit logging
    - Ensure all Lambda functions log to AuditLogs
    - Include timestamp, actor, action type, entity ID, details
    - Include AI reasoning for matching decisions
    - Include approver identity for human actions
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  
  - [ ]* 11.3 Write property test for audit logging
    - **Property 28: Comprehensive Audit Logging**
    - **Validates: Requirements 10.1, 10.4**

- [ ] 12. Error Handling & Resilience (Day 7)
  - [ ] 12.1 Implement Lambda retry logic
    - Add exponential backoff for DynamoDB throttling
    - Add retry logic for Bedrock API failures
    - Add error logging to CloudWatch
    - _Requirements: 16.1, 16.3, 16.4, 16.5_
  
  - [ ] 12.2 Implement error notification system
    - Create SNS topic for admin notifications
    - Subscribe admin emails to topic
    - Send notifications on critical errors (Step Function failures, prolonged AI unavailability)
    - _Requirements: 16.6_
  
  - [ ]* 12.3 Write property test for retry logic
    - **Property 31: Step Function Retry Logic**
    - **Validates: Requirements 11.4, 16.1**

- [ ] 13. Final Integration & Testing (Day 7)
  - [ ] 13.1 Deploy full stack to AWS
    - Deploy CDK infrastructure (DynamoDB, S3, Lambda, Step Functions, API Gateway)
    - Deploy Amplify frontend
    - Configure environment variables
    - Verify all services are connected
    - _Requirements: All_
  
  - [ ] 13.2 End-to-end testing
    - Test email ingestion → PDF extraction → AI matching → fraud detection → approval
    - Test PO upload and search
    - Test invoice approval and rejection
    - Test audit trail
    - Verify AWS Free Tier usage is within limits
    - _Requirements: All_
  
  - [ ] 13.3 Create demo data and walkthrough
    - Upload sample POs
    - Send sample invoice emails
    - Demonstrate auto-approval for perfect match
    - Demonstrate human approval for flagged invoice
    - Show audit trail
    - _Requirements: All_

- [ ] 14. Final Checkpoint - Production Ready
  - Ensure all critical tests pass
  - Verify AWS Free Tier compliance
  - Confirm all core features working
  - Ask the user if questions arise or if ready to submit.

## Notes

- Tasks marked with `*` are optional property/unit tests - implement if time permits, skip for faster MVP
- Focus on getting core workflow working first (Tasks 1-6)
- Frontend can be simplified with minimal styling for MVP
- Advanced fraud detection can be added post-MVP
- Comprehensive error handling can be simplified for MVP (basic retries only)
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation

## MVP vs Full Feature Comparison

**MVP (1 Week)**:
- ✅ Core invoice processing pipeline
- ✅ Basic AI matching with explainability
- ✅ Basic fraud detection (2-3 patterns)
- ✅ Human approval workflow
- ✅ Functional dashboard
- ✅ Basic audit logging
- ⚠️ Simplified error handling
- ⚠️ Minimal UI polish

**Full Feature (7 Weeks)**:
- ✅ All MVP features
- ✅ Comprehensive fraud detection (all patterns)
- ✅ Advanced error handling with all retry strategies
- ✅ Polished UI with animations and responsive design
- ✅ Advanced audit trail with export and analytics
- ✅ Email configuration UI
- ✅ Comprehensive monitoring and alerting
- ✅ Full property-based test coverage
