# Implementation Plan: Settings Page

## Overview

This implementation plan creates a comprehensive Settings Page feature for ReconcileAI with role-based access control, system configuration management, theme customization, notification preferences, and API key management. The feature uses AWS Lambda (Python 3.11 on ARM64), DynamoDB, API Gateway with Cognito authorization, and a React frontend. All settings changes are audited to maintain compliance tracking.

## Tasks

- [ ] 1. Set up DynamoDB Settings Table and infrastructure
  - Create Settings table with composite key (settingType, settingKey)
  - Add UserIdIndex GSI for efficient user settings queries
  - Configure On-Demand billing mode for Free Tier compliance
  - Add table to CDK/SAM infrastructure stack
  - _Requirements: 6.1, 6.2, 11.2_

- [ ] 2. Implement Settings Lambda function core logic
  - [ ] 2.1 Create Lambda function structure and handler
    - Set up Python 3.11 Lambda with ARM64 architecture
    - Configure 256MB memory and 30-second timeout
    - Add environment variables for table names and cache TTL
    - Implement main lambda_handler with HTTP method routing
    - _Requirements: 7.1, 7.2, 7.5, 11.1, 11.5_
  
  - [ ] 2.2 Implement JWT token extraction and role validation
    - Extract user identity and role from Cognito JWT token
    - Create check_role_permission function for role-based access
    - Handle authentication errors (401) and authorization errors (403)
    - _Requirements: 1.3, 1.4, 7.5_
  
  - [ ] 2.3 Implement GET /settings endpoint
    - Query DynamoDB for user settings using UserIdIndex
    - Query system settings if user has Admin role
    - Filter results based on user role
    - Implement response caching with 5-minute TTL
    - Return combined settings object
    - _Requirements: 1.1, 1.2, 7.1, 11.3_
  
  - [ ] 2.4 Implement PUT /settings/{settingType}/{settingKey} endpoint
    - Extract settingType, settingKey, value, and version from request
    - Validate role permission for the setting type
    - Call validate_setting_value function
    - Update DynamoDB with optimistic locking (conditional update on version)
    - Handle ConditionalCheckFailedException for conflicts (409)
    - Invalidate cache after successful update
    - _Requirements: 2.2, 2.3, 6.3, 6.5, 7.2_

- [ ] 3. Implement input validation and sanitization
  - [ ] 3.1 Create validation rules configuration
    - Define VALIDATION_RULES dictionary with constraints for all settings
    - Include type, min/max, enum values, and required flags
    - _Requirements: 8.1, 8.3, 8.4_
  
  - [ ] 3.2 Implement validate_setting_value function
    - Validate number types with min/max range checks
    - Validate enum types against allowed values
    - Validate boolean types
    - Validate object types with nested schema validation
    - Return ValidationError with detailed messages for failures
    - _Requirements: 2.2, 8.1, 8.3_
  
  - [ ] 3.3 Implement sanitize_string function
    - Truncate strings to maximum length (255 chars)
    - HTML escape all string inputs
    - Remove SQL injection patterns (SELECT, INSERT, --, etc.)
    - Remove XSS patterns (script tags, javascript:, event handlers)
    - Remove shell command patterns ($, backticks, pipes)
    - _Requirements: 8.2, 8.6_
  
  - [ ] 3.4 Implement sanitize_email function
    - Validate email format using RFC 5322 regex
    - Convert to lowercase and trim whitespace
    - Return ValidationError for invalid formats
    - _Requirements: 8.5_

- [ ] 4. Implement audit logging for settings changes
  - [ ] 4.1 Create audit logging helper function
    - Accept entity_type, entity_id, action, user_id, and details parameters
    - Generate UUID for LogId
    - Create ISO 8601 timestamp
    - Write to AuditLogs table asynchronously
    - _Requirements: 9.1, 9.2_
  
  - [ ] 4.2 Integrate audit logging into settings updates
    - Log all Create, Update, and Delete actions
    - Include old value and new value in details
    - Extract IP address from event context
    - Handle audit logging failures gracefully (log to CloudWatch, don't block operation)
    - Ensure logging completes within 100ms
    - _Requirements: 2.4, 9.1, 9.2, 9.4, 9.5_

- [ ] 5. Implement API Key Manager Lambda function
  - [ ] 5.1 Create API Key Manager Lambda structure
    - Set up Python 3.11 Lambda with ARM64 architecture
    - Configure 256MB memory and 30-second timeout
    - Add environment variables for table names
    - Implement main lambda_handler with endpoint routing
    - _Requirements: 5.2, 11.1, 11.5_
  
  - [ ] 5.2 Implement POST /settings/api-keys endpoint
    - Validate user has Admin role (403 if not)
    - Generate 32-character cryptographically secure random key using secrets module
    - Create SHA-256 hash of the key for storage
    - Extract last 4 characters for display
    - Store key hash, last 4 chars, description, createdAt, createdBy, and status in DynamoDB
    - Return full API key in response (shown only once)
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [ ] 5.3 Implement GET /settings/api-keys endpoint
    - Validate user has Admin role (403 if not)
    - Query DynamoDB for all api-key settingType entries
    - Return list with keyId, lastFourChars, createdAt, description, and status
    - Never return full key or key hash
    - _Requirements: 5.1, 5.5_
  
  - [ ] 5.4 Implement DELETE /settings/api-keys/{keyId} endpoint
    - Validate user has Admin role (403 if not)
    - Update DynamoDB to set status to "revoked"
    - Add revokedAt timestamp and revokedBy userId
    - Return success response
    - _Requirements: 5.1, 5.6_
  
  - [ ] 5.5 Implement POST /settings/api-keys/validate endpoint (internal)
    - Accept API key in request body
    - Create SHA-256 hash of the key
    - Query DynamoDB for matching keyHash with status "active"
    - Return 200 if valid, 401 if invalid or revoked
    - _Requirements: 5.7, 5.8_
  
  - [ ] 5.6 Add audit logging for API key operations
    - Log APIKeyGenerated action when key is created
    - Log APIKeyRevoked action when key is revoked
    - Include key identifier and admin username in details
    - _Requirements: 9.3_

- [ ] 6. Implement error handling and retry logic
  - [ ] 6.1 Add comprehensive error handling to Lambda functions
    - Catch AuthenticationError and return 401 with AUTH_REQUIRED code
    - Catch AuthorizationError and return 403 with FORBIDDEN code
    - Catch ValidationError and return 400 with VALIDATION_ERROR code and details
    - Catch ConflictError and return 409 with CONFLICT code and current version
    - Catch DynamoDB ClientError and map to appropriate HTTP status codes
    - Catch generic exceptions and return 500 with INTERNAL_ERROR code
    - Log all errors to CloudWatch with full stack traces
    - _Requirements: 12.1, 12.2, 12.5_
  
  - [ ] 6.2 Implement retry logic with exponential backoff
    - Create retry_with_backoff decorator function
    - Configure max 3 attempts, initial 100ms delay, 2.0 backoff rate, max 1000ms delay
    - Add jitter to prevent thundering herd
    - Retry on ProvisionedThroughputExceededException, RequestLimitExceeded, InternalServerError, ServiceUnavailable
    - _Requirements: 12.4_
  
  - [ ] 6.3 Add CloudWatch metrics for monitoring
    - Emit AuditLogFailure metric when audit logging fails
    - Emit SettingsUpdateFailure metric for failed updates
    - Emit APIKeyValidationFailure metric for invalid key attempts
    - _Requirements: 9.5_

- [ ] 7. Configure API Gateway endpoints with Cognito authorization
  - [ ] 7.1 Create API Gateway REST API resource
    - Create /settings resource
    - Create /settings/{settingType}/{settingKey} resource with path parameters
    - Create /settings/api-keys resource
    - Create /settings/api-keys/{keyId} resource with path parameter
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  
  - [ ] 7.2 Configure Cognito Authorizer
    - Create Cognito User Pool Authorizer
    - Configure to validate JWT tokens from Authorization header
    - Extract user identity and role claims
    - Attach authorizer to all settings endpoints
    - _Requirements: 1.3, 7.5_
  
  - [ ] 7.3 Configure method integrations
    - Link GET /settings to Settings Lambda
    - Link PUT /settings/{settingType}/{settingKey} to Settings Lambda
    - Link POST /settings/api-keys to API Key Manager Lambda
    - Link GET /settings/api-keys to API Key Manager Lambda
    - Link DELETE /settings/api-keys/{keyId} to API Key Manager Lambda
    - Configure request/response mappings for JSON
    - Enable CORS for all endpoints
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.6_

- [ ] 8. Implement React Settings Page frontend
  - [ ] 8.1 Create SettingsPage component structure
    - Create SettingsPage.tsx with main container component
    - Add state management for settings, loading, error, isDirty
    - Implement useEffect to fetch settings on mount
    - Use AuthContext to get user identity and role
    - Create SettingsPage.css for styling
    - _Requirements: 10.1, 10.6_
  
  - [ ] 8.2 Implement settings fetching logic
    - Create fetchSettings async function
    - Call GET /settings with JWT token in Authorization header
    - Handle loading state and error responses
    - Parse response and update state
    - Display error messages for failed requests
    - _Requirements: 10.6_
  
  - [ ] 8.3 Implement settings saving logic
    - Create saveSettings async function
    - Call PUT /settings/{settingType}/{settingKey} with value and version
    - Handle 400 validation errors with inline messages
    - Handle 409 conflict errors with refresh prompt
    - Handle 403 authorization errors
    - Handle 503 service unavailable with retry logic
    - Display success message for 3 seconds after successful save
    - Clear isDirty flag after successful save
    - _Requirements: 10.3, 10.4, 10.5, 12.3, 12.6_
  
  - [ ] 8.4 Create collapsible section components
    - Create Section component with title and collapsible content
    - Organize settings into System Configuration, Appearance, Notifications, and API Keys sections
    - Implement expand/collapse functionality
    - _Requirements: 10.1_

- [ ] 9. Implement SystemConfigSection component (Admin only)
  - [ ] 9.1 Create SystemConfigSection component
    - Render only if user role is Admin
    - Display reconciliation threshold input (number, 0-100)
    - Display auto-approval limit input (currency, 0-10000)
    - Display fraud detection sensitivity dropdown (low/medium/high)
    - Implement onChange handlers to update state and set isDirty flag
    - _Requirements: 1.1, 2.1, 10.2_
  
  - [ ] 9.2 Add client-side validation
    - Validate reconciliation threshold range before submission
    - Validate auto-approval limit range before submission
    - Validate fraud detection sensitivity enum value
    - Display inline validation errors
    - Disable save button if validation fails
    - _Requirements: 10.7_

- [ ] 10. Implement ThemeEngine and appearance settings
  - [ ] 10.1 Create ThemeEngine utility
    - Create applyTheme function to update CSS variables
    - Define light theme CSS variables (background, text, primary colors)
    - Define dark theme CSS variables
    - Apply theme changes to document root without page refresh
    - _Requirements: 3.2, 3.6_
  
  - [ ] 10.2 Create AppearanceSection component
    - Display theme selector with Light and Dark options
    - Implement onChange handler to call applyTheme and update backend
    - Load saved theme preference on component mount
    - Default to Light mode if no preference exists
    - _Requirements: 3.1, 3.3, 3.4, 3.5_

- [ ] 11. Implement NotificationPreferencesSection component
  - [ ] 11.1 Create NotificationPreferencesSection component
    - Display toggle switches for invoice received, reconciliation completed, discrepancy detected, and approval required
    - Implement onChange handlers to update state and set isDirty flag
    - Load current notification preferences from settings
    - _Requirements: 4.1, 4.5_
  
  - [ ] 11.2 Implement notification preference persistence
    - Call PUT /settings/user/notifications with updated preferences object
    - Handle save success and error states
    - _Requirements: 4.2_
  
  - [ ] 11.3 Initialize default notification preferences for new users
    - Check if notification preferences exist in settings
    - If not, initialize with all notifications enabled
    - Save defaults to backend
    - _Requirements: 4.6_

- [ ] 12. Implement APIKeyManagementSection component (Admin only)
  - [ ] 12.1 Create APIKeyManagementSection component structure
    - Render only if user role is Admin
    - Add state for API keys list, generated key, and loading states
    - Create APIKeyManagementSection.css for styling
    - _Requirements: 5.1_
  
  - [ ] 12.2 Implement API key generation UI
    - Add "Generate New API Key" button
    - Display modal/dialog for key description input
    - Call POST /settings/api-keys with description
    - Display generated key in modal with copy-to-clipboard button
    - Show warning that key will only be displayed once
    - Clear generated key from state after modal is closed
    - _Requirements: 5.2, 5.3, 5.4_
  
  - [ ] 12.3 Implement API key listing UI
    - Fetch and display list of existing API keys on component mount
    - Display table with columns: Last 4 Chars, Description, Created Date, Status, Actions
    - Mask key values showing only last 4 characters
    - Display creation date in user-friendly format
    - _Requirements: 5.5_
  
  - [ ] 12.4 Implement API key revocation UI
    - Add "Revoke" button for each active key
    - Display confirmation dialog before revocation
    - Call DELETE /settings/api-keys/{keyId}
    - Update list to show revoked status
    - _Requirements: 5.6_

- [ ] 13. Add form controls and validation UI
  - [ ] 13.1 Create reusable form control components
    - Create NumberInput component with min/max validation
    - Create Dropdown component for enum values
    - Create Toggle component for boolean settings
    - Create TextInput component with sanitization
    - _Requirements: 10.2_
  
  - [ ] 13.2 Implement inline validation error display
    - Display validation errors below each form control
    - Style error messages in red with icon
    - Clear errors when user corrects input
    - _Requirements: 10.7_
  
  - [ ] 13.3 Implement save button state management
    - Enable save button only when isDirty is true and validation passes
    - Disable save button during save operation (loading state)
    - Display loading spinner on button during save
    - _Requirements: 10.3_

- [ ] 14. Implement settings caching in Lambda
  - [ ] 14.1 Add in-memory cache to Settings Lambda
    - Create cache dictionary with TTL tracking
    - Implement get_cached_settings function
    - Implement set_cached_settings function with 5-minute TTL
    - Check cache before querying DynamoDB
    - _Requirements: 11.3_
  
  - [ ] 14.2 Implement cache invalidation
    - Clear cache entry after successful setting update
    - Clear entire cache if TTL expires
    - _Requirements: 11.3_

- [ ] 15. Add DynamoDB connection pooling
  - [ ] 15.1 Configure boto3 DynamoDB client with connection pooling
    - Create DynamoDB client outside lambda_handler for reuse across invocations
    - Configure max_pool_connections to 10
    - Implement connection retry configuration
    - _Requirements: 11.6_

- [ ] 16. Write unit tests for Settings Lambda
  - [ ]* 16.1 Write tests for role-based access control
    - Test admin user receives all settings
    - Test standard user receives only personal settings
    - Test standard user cannot update system settings (403)
    - _Requirements: 1.1, 1.2, 1.4_
  
  - [ ]* 16.2 Write tests for input validation
    - Test numeric settings reject out-of-range values (400)
    - Test enum settings reject invalid values (400)
    - Test string sanitization removes SQL injection patterns
    - Test string sanitization removes XSS patterns
    - Test string sanitization removes shell command patterns
    - Test email validation rejects invalid formats
    - _Requirements: 8.1, 8.2, 8.3, 8.5, 8.6_
  
  - [ ]* 16.3 Write tests for optimistic locking
    - Test concurrent update detection returns 409
    - Test version increment after successful update
    - _Requirements: 6.5, 6.6_
  
  - [ ]* 16.4 Write tests for audit logging
    - Test settings changes are logged to AuditLogs table
    - Test audit log includes old value, new value, timestamp, and username
    - Test settings update succeeds even if audit logging fails
    - _Requirements: 9.1, 9.2, 9.5_
  
  - [ ]* 16.5 Write tests for caching
    - Test repeated requests within TTL use cached response
    - Test cache is invalidated after update
    - _Requirements: 11.3_
  
  - [ ]* 16.6 Write tests for error handling
    - Test invalid JWT returns 401
    - Test DynamoDB unavailable returns 503
    - Test retry logic handles transient errors
    - _Requirements: 12.1, 12.2, 12.4_

- [ ] 17. Write unit tests for API Key Manager Lambda
  - [ ]* 17.1 Write tests for API key generation
    - Test generated keys are 32 characters long
    - Test only SHA-256 hash is stored in DynamoDB
    - Test standard user cannot generate keys (403)
    - _Requirements: 5.2, 5.3_
  
  - [ ]* 17.2 Write tests for API key listing
    - Test listed keys show only last 4 characters
    - Test admin user can list all keys
    - _Requirements: 5.5_
  
  - [ ]* 17.3 Write tests for API key revocation
    - Test revoked keys are marked inactive, not deleted
    - Test revoked keys fail validation (401)
    - _Requirements: 5.6, 5.8_
  
  - [ ]* 17.4 Write tests for API key validation
    - Test valid active keys pass validation
    - Test invalid keys fail validation (401)
    - Test revoked keys fail validation (401)
    - _Requirements: 5.7, 5.8_
  
  - [ ]* 17.5 Write tests for audit logging
    - Test key generation is logged
    - Test key revocation is logged
    - _Requirements: 9.3_

- [ ] 18. Write unit tests for React components
  - [ ]* 18.1 Write tests for SettingsPage component
    - Test renders correctly for Admin users (shows all sections)
    - Test renders correctly for Standard users (hides admin sections)
    - Test displays loading state while fetching settings
    - Test displays error messages when API calls fail
    - Test enables save button when settings are modified
    - Test shows success message after successful save
    - Test handles 409 Conflict errors with refresh prompt
    - _Requirements: 1.1, 1.2, 10.3, 10.4, 10.5, 10.6_
  
  - [ ]* 18.2 Write tests for ThemeEngine
    - Test applies light theme CSS variables correctly
    - Test applies dark theme CSS variables correctly
    - Test persists theme selection to backend
    - Test loads saved theme preference on mount
    - Test defaults to light theme when no preference exists
    - Test applies theme changes without page refresh
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_
  
  - [ ]* 18.3 Write tests for SystemConfigSection
    - Test validates reconciliation threshold range (0-100)
    - Test validates auto-approval limit range (0-10000)
    - Test validates fraud detection sensitivity enum values
    - Test displays validation errors inline
    - Test only renders for Admin users
    - _Requirements: 1.1, 2.1, 10.2, 10.7_
  
  - [ ]* 18.4 Write tests for NotificationPreferencesSection
    - Test toggles notification preferences correctly
    - Test initializes with all notifications enabled for new users
    - Test persists changes to backend
    - _Requirements: 4.1, 4.2, 4.6_
  
  - [ ]* 18.5 Write tests for APIKeyManagementSection
    - Test generates new API key and displays it once
    - Test copies API key to clipboard
    - Test lists existing keys with masked values
    - Test revokes API key with confirmation
    - Test only renders for Admin users
    - _Requirements: 5.1, 5.2, 5.4, 5.5, 5.6_

- [ ] 19. Checkpoint - Ensure all tests pass
  - Run all unit tests for Lambda functions and React components
  - Verify test coverage meets minimum thresholds
  - Fix any failing tests
  - Ensure all tests pass, ask the user if questions arise

- [ ] 20. Deploy infrastructure and test end-to-end
  - [ ] 20.1 Deploy DynamoDB Settings table
    - Deploy table using CDK/SAM
    - Verify table creation and indexes
    - _Requirements: 6.1, 6.2_
  
  - [ ] 20.2 Deploy Lambda functions
    - Deploy Settings Lambda with correct IAM permissions
    - Deploy API Key Manager Lambda with correct IAM permissions
    - Verify Lambda functions are created with ARM64 architecture
    - Verify environment variables are set correctly
    - _Requirements: 11.1, 11.5_
  
  - [ ] 20.3 Deploy API Gateway endpoints
    - Deploy API Gateway with Cognito Authorizer
    - Verify all endpoints are configured correctly
    - Test CORS configuration
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  
  - [ ] 20.4 Deploy React frontend
    - Build React app with settings page
    - Deploy to AWS Amplify or S3 + CloudFront
    - Update API endpoint configuration
    - _Requirements: 10.1_
  
  - [ ] 20.5 Test end-to-end workflows
    - Test admin user can access all settings
    - Test standard user can only access personal settings
    - Test theme switching works without page refresh
    - Test notification preferences are persisted
    - Test API key generation, listing, and revocation
    - Test settings changes are audited
    - Test error handling for validation failures
    - Test error handling for concurrent updates
    - Verify AWS Free Tier compliance (check DynamoDB metrics, Lambda invocations)
    - _Requirements: All_

- [ ] 21. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- All Lambda functions use Python 3.11 on ARM64 for Free Tier optimization
- DynamoDB uses On-Demand mode to stay within Free Tier limits
- Response caching reduces DynamoDB read operations
- All settings changes are audited for compliance
- Role-based access control ensures security
- Input validation and sanitization protect against injection attacks
