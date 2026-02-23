import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as ses from 'aws-cdk-lib/aws-ses';
import * as sesActions from 'aws-cdk-lib/aws-ses-actions';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as path from 'path';

export class ReconcileAIStack extends cdk.Stack {
  public readonly posTable: dynamodb.Table;
  public readonly invoicesTable: dynamodb.Table;
  public readonly auditLogsTable: dynamodb.Table;
  public readonly invoiceBucket: s3.Bucket;
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;
  public readonly adminGroup: cognito.CfnUserPoolGroup;
  public readonly userGroup: cognito.CfnUserPoolGroup;
  public readonly pdfExtractionLambda: lambda.Function;
  public readonly aiMatchingLambda: lambda.Function;
  public readonly fraudDetectionLambda: lambda.Function;
  public readonly resolveStepLambda: lambda.Function;
  public readonly invoiceProcessingStateMachine: sfn.StateMachine;
  public readonly poManagementLambda: lambda.Function;
  public readonly invoiceManagementLambda: lambda.Function;
  public readonly api: apigateway.RestApi;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ========================================
    // DynamoDB Tables (On-Demand for Free Tier)
    // ========================================

    // POs Table
    this.posTable = new dynamodb.Table(this, 'POsTable', {
      tableName: 'ReconcileAI-POs',
      partitionKey: {
        name: 'POId',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST, // On-Demand mode for Free Tier
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: false, // Disabled to stay in Free Tier
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For dev environment
    });

    // GSI for querying by VendorName
    this.posTable.addGlobalSecondaryIndex({
      indexName: 'VendorNameIndex',
      partitionKey: {
        name: 'VendorName',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'UploadDate',
        type: dynamodb.AttributeType.STRING,
      },
    });

    // Invoices Table
    this.invoicesTable = new dynamodb.Table(this, 'InvoicesTable', {
      tableName: 'ReconcileAI-Invoices',
      partitionKey: {
        name: 'InvoiceId',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST, // On-Demand mode for Free Tier
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: false, // Disabled to stay in Free Tier
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For dev environment
    });

    // GSI for querying by VendorName
    this.invoicesTable.addGlobalSecondaryIndex({
      indexName: 'VendorNameIndex',
      partitionKey: {
        name: 'VendorName',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'ReceivedDate',
        type: dynamodb.AttributeType.STRING,
      },
    });

    // GSI for querying by Status
    this.invoicesTable.addGlobalSecondaryIndex({
      indexName: 'StatusIndex',
      partitionKey: {
        name: 'Status',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'ReceivedDate',
        type: dynamodb.AttributeType.STRING,
      },
    });

    // AuditLogs Table
    this.auditLogsTable = new dynamodb.Table(this, 'AuditLogsTable', {
      tableName: 'ReconcileAI-AuditLogs',
      partitionKey: {
        name: 'LogId',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'Timestamp',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST, // On-Demand mode for Free Tier
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: false, // Disabled to stay in Free Tier
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For dev environment
    });

    // GSI for querying by EntityId
    this.auditLogsTable.addGlobalSecondaryIndex({
      indexName: 'EntityIdIndex',
      partitionKey: {
        name: 'EntityId',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'Timestamp',
        type: dynamodb.AttributeType.STRING,
      },
    });

    // Output table names for reference
    new cdk.CfnOutput(this, 'POsTableName', {
      value: this.posTable.tableName,
      description: 'DynamoDB table for Purchase Orders',
    });

    new cdk.CfnOutput(this, 'InvoicesTableName', {
      value: this.invoicesTable.tableName,
      description: 'DynamoDB table for Invoices',
    });

    new cdk.CfnOutput(this, 'AuditLogsTableName', {
      value: this.auditLogsTable.tableName,
      description: 'DynamoDB table for Audit Logs',
    });

    // ========================================
    // S3 Bucket for PDF Storage
    // ========================================

    this.invoiceBucket = new s3.Bucket(this, 'InvoiceBucket', {
      bucketName: `reconcileai-invoices-${this.account}`,
      encryption: s3.BucketEncryption.S3_MANAGED, // SSE-S3 encryption
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: false, // Disabled to save storage in Free Tier
      lifecycleRules: [
        {
          id: 'DeleteOldInvoices',
          enabled: true,
          expiration: cdk.Duration.days(365), // Keep invoices for 1 year
        },
      ],
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For dev environment
      autoDeleteObjects: true, // Clean up on stack deletion
    });

    // Output bucket name
    new cdk.CfnOutput(this, 'InvoiceBucketName', {
      value: this.invoiceBucket.bucketName,
      description: 'S3 bucket for invoice PDFs',
    });

    // ========================================
    // Amazon Cognito User Pool
    // ========================================

    this.userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName: 'ReconcileAI-Users',
      selfSignUpEnabled: false, // Admin creates users
      signInAliases: {
        email: true,
        username: false,
      },
      autoVerify: {
        email: true,
      },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      standardAttributes: {
        email: {
          required: true,
          mutable: true,
        },
        fullname: {
          required: true,
          mutable: true,
        },
      },
      customAttributes: {
        role: new cognito.StringAttribute({ 
          minLen: 4, 
          maxLen: 10,
          mutable: true,
        }),
      },
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For dev environment
    });

    // User Pool Client for frontend
    this.userPoolClient = new cognito.UserPoolClient(this, 'UserPoolClient', {
      userPool: this.userPool,
      userPoolClientName: 'ReconcileAI-WebClient',
      authFlows: {
        userPassword: true,
        userSrp: true,
      },
      generateSecret: false, // No secret for public clients (web/mobile)
      preventUserExistenceErrors: true,
    });

    // Admin Group
    this.adminGroup = new cognito.CfnUserPoolGroup(this, 'AdminGroup', {
      userPoolId: this.userPool.userPoolId,
      groupName: 'Admin',
      description: 'Administrators with full system access',
      precedence: 1,
    });

    // User Group
    this.userGroup = new cognito.CfnUserPoolGroup(this, 'UserGroup', {
      userPoolId: this.userPool.userPoolId,
      groupName: 'User',
      description: 'Standard users with limited access',
      precedence: 2,
    });

    // Output Cognito details
    new cdk.CfnOutput(this, 'UserPoolId', {
      value: this.userPool.userPoolId,
      description: 'Cognito User Pool ID',
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: this.userPoolClient.userPoolClientId,
      description: 'Cognito User Pool Client ID',
    });

    // ========================================
    // Amazon SES Email Receiving
    // ========================================

    // Grant SES permission to write to S3 bucket
    this.invoiceBucket.addToResourcePolicy(
      new iam.PolicyStatement({
        sid: 'AllowSESPuts',
        effect: iam.Effect.ALLOW,
        principals: [new iam.ServicePrincipal('ses.amazonaws.com')],
        actions: ['s3:PutObject'],
        resources: [`${this.invoiceBucket.bucketArn}/*`],
        conditions: {
          StringEquals: {
            'AWS:SourceAccount': this.account,
          },
        },
      })
    );

    // SES Receipt Rule Set (must be created manually or via CLI)
    // Note: Only one active rule set is allowed per region
    const receiptRuleSet = new ses.ReceiptRuleSet(this, 'ReceiptRuleSet', {
      receiptRuleSetName: 'ReconcileAI-RuleSet',
    });

    // SES Receipt Rule to save emails to S3
    const receiptRule = new ses.ReceiptRule(this, 'InvoiceReceiptRule', {
      ruleSet: receiptRuleSet,
      recipients: [], // Will be configured manually after domain verification
      actions: [
        new sesActions.S3({
          bucket: this.invoiceBucket,
          objectKeyPrefix: 'emails/',
        }),
      ],
      enabled: true,
      scanEnabled: true, // Enable spam and virus scanning
    });

    // Output SES configuration
    new cdk.CfnOutput(this, 'SESRuleSetName', {
      value: receiptRuleSet.receiptRuleSetName,
      description: 'SES Receipt Rule Set Name',
    });

    new cdk.CfnOutput(this, 'SESSetupInstructions', {
      value: 'See docs/SES_SETUP.md for email verification and configuration steps',
      description: 'SES Setup Instructions',
    });

    // ========================================
    // Lambda Functions
    // ========================================

    // PDF Extraction Lambda Function
    this.pdfExtractionLambda = new lambda.Function(this, 'PDFExtractionLambda', {
      functionName: 'ReconcileAI-PDFExtraction',
      runtime: lambda.Runtime.PYTHON_3_11,
      architecture: lambda.Architecture.ARM_64, // ARM/Graviton2 for cost efficiency
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../lambda/pdf-extraction')),
      timeout: cdk.Duration.seconds(60), // PDF extraction can take time
      memorySize: 512, // Sufficient for PDF processing
      environment: {
        INVOICES_TABLE_NAME: this.invoicesTable.tableName,
        AUDIT_LOGS_TABLE_NAME: this.auditLogsTable.tableName,
      },
      layers: [
        // Lambda layer for pdfplumber will be created separately
        // For now, we'll package dependencies with the function
      ],
    });

    // Grant Lambda permissions to read from S3
    this.invoiceBucket.grantRead(this.pdfExtractionLambda);

    // Grant Lambda permissions to write to DynamoDB tables
    this.invoicesTable.grantWriteData(this.pdfExtractionLambda);
    this.auditLogsTable.grantWriteData(this.pdfExtractionLambda);

    // Output Lambda function name
    new cdk.CfnOutput(this, 'PDFExtractionLambdaName', {
      value: this.pdfExtractionLambda.functionName,
      description: 'PDF Extraction Lambda Function Name',
    });

    new cdk.CfnOutput(this, 'PDFExtractionLambdaArn', {
      value: this.pdfExtractionLambda.functionArn,
      description: 'PDF Extraction Lambda Function ARN',
    });

    // AI Matching Lambda Function
    this.aiMatchingLambda = new lambda.Function(this, 'AIMatchingLambda', {
      functionName: 'ReconcileAI-AIMatching',
      runtime: lambda.Runtime.PYTHON_3_11,
      architecture: lambda.Architecture.ARM_64, // ARM/Graviton2 for cost efficiency
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../lambda/ai-matching')),
      timeout: cdk.Duration.seconds(60), // AI matching can take time
      memorySize: 512, // Sufficient for AI operations
      environment: {
        POS_TABLE_NAME: this.posTable.tableName,
        INVOICES_TABLE_NAME: this.invoicesTable.tableName,
        AUDIT_LOGS_TABLE_NAME: this.auditLogsTable.tableName,
        AWS_REGION: this.region,
      },
    });

    // Grant Lambda permissions to read from POs table
    this.posTable.grantReadData(this.aiMatchingLambda);

    // Grant Lambda permissions to read/write to Invoices table
    this.invoicesTable.grantReadWriteData(this.aiMatchingLambda);

    // Grant Lambda permissions to write to AuditLogs table
    this.auditLogsTable.grantWriteData(this.aiMatchingLambda);

    // Grant Lambda permissions to invoke Bedrock
    this.aiMatchingLambda.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['bedrock:InvokeModel'],
        resources: [
          `arn:aws:bedrock:${this.region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0`,
        ],
      })
    );

    // Output Lambda function details
    new cdk.CfnOutput(this, 'AIMatchingLambdaName', {
      value: this.aiMatchingLambda.functionName,
      description: 'AI Matching Lambda Function Name',
    });

    new cdk.CfnOutput(this, 'AIMatchingLambdaArn', {
      value: this.aiMatchingLambda.functionArn,
      description: 'AI Matching Lambda Function ARN',
    });

    // Fraud Detection Lambda Function
    this.fraudDetectionLambda = new lambda.Function(this, 'FraudDetectionLambda', {
      functionName: 'ReconcileAI-FraudDetection',
      runtime: lambda.Runtime.PYTHON_3_11,
      architecture: lambda.Architecture.ARM_64, // ARM/Graviton2 for cost efficiency
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../lambda/fraud-detection')),
      timeout: cdk.Duration.seconds(30), // Fraud detection is fast
      memorySize: 256, // Minimal memory needed
      environment: {
        POS_TABLE_NAME: this.posTable.tableName,
        INVOICES_TABLE_NAME: this.invoicesTable.tableName,
        AUDIT_LOGS_TABLE_NAME: this.auditLogsTable.tableName,
      },
    });

    // Grant Lambda permissions to read from POs and Invoices tables
    this.posTable.grantReadData(this.fraudDetectionLambda);
    this.invoicesTable.grantReadWriteData(this.fraudDetectionLambda);
    this.auditLogsTable.grantWriteData(this.fraudDetectionLambda);

    // Output Lambda function details
    new cdk.CfnOutput(this, 'FraudDetectionLambdaName', {
      value: this.fraudDetectionLambda.functionName,
      description: 'Fraud Detection Lambda Function Name',
    });

    new cdk.CfnOutput(this, 'FraudDetectionLambdaArn', {
      value: this.fraudDetectionLambda.functionArn,
      description: 'Fraud Detection Lambda Function ARN',
    });

    // Resolve Step Lambda Function (Auto-approval logic)
    this.resolveStepLambda = new lambda.Function(this, 'ResolveStepLambda', {
      functionName: 'ReconcileAI-ResolveStep',
      runtime: lambda.Runtime.PYTHON_3_11,
      architecture: lambda.Architecture.ARM_64, // ARM/Graviton2 for cost efficiency
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../lambda/resolve-step')),
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      environment: {
        INVOICES_TABLE_NAME: this.invoicesTable.tableName,
        AUDIT_LOGS_TABLE_NAME: this.auditLogsTable.tableName,
      },
    });

    // Grant Lambda permissions
    this.invoicesTable.grantReadWriteData(this.resolveStepLambda);
    this.auditLogsTable.grantWriteData(this.resolveStepLambda);

    // Output Lambda function details
    new cdk.CfnOutput(this, 'ResolveStepLambdaName', {
      value: this.resolveStepLambda.functionName,
      description: 'Resolve Step Lambda Function Name',
    });

    new cdk.CfnOutput(this, 'ResolveStepLambdaArn', {
      value: this.resolveStepLambda.functionArn,
      description: 'Resolve Step Lambda Function ARN',
    });

    // ========================================
    // Step Functions State Machine (4 steps: Extract → Match → Detect → Resolve)
    // ========================================

    // Step 1: Extract - PDF text extraction
    const extractTask = new tasks.LambdaInvoke(this, 'ExtractInvoiceData', {
      lambdaFunction: this.pdfExtractionLambda,
      outputPath: '$.Payload',
      retryOnServiceExceptions: true,
    });

    // Step 2: Match - AI matching against POs
    const matchTask = new tasks.LambdaInvoke(this, 'MatchInvoiceToPOs', {
      lambdaFunction: this.aiMatchingLambda,
      outputPath: '$.Payload',
      retryOnServiceExceptions: true,
    });

    // Step 3: Detect - Fraud detection
    const detectTask = new tasks.LambdaInvoke(this, 'DetectFraud', {
      lambdaFunction: this.fraudDetectionLambda,
      outputPath: '$.Payload',
      retryOnServiceExceptions: true,
    });

    // Step 4: Resolve - Auto-approval or flag for human review
    const resolveTask = new tasks.LambdaInvoke(this, 'ResolveInvoice', {
      lambdaFunction: this.resolveStepLambda,
      outputPath: '$.Payload',
      retryOnServiceExceptions: true,
    });

    // Configure retry logic for all tasks (3 retries with exponential backoff)
    const retryConfig = {
      errors: ['States.TaskFailed', 'States.Timeout', 'Lambda.ServiceException'],
      interval: cdk.Duration.seconds(2),
      maxAttempts: 3,
      backoffRate: 2.0,
    };

    extractTask.addRetry(retryConfig);
    matchTask.addRetry(retryConfig);
    detectTask.addRetry(retryConfig);
    resolveTask.addRetry(retryConfig);

    // Flag for manual review state (when all retries fail)
    const flagForManualReview = new sfn.Succeed(this, 'FlaggedForManualReview', {
      comment: 'Invoice flagged for manual review due to processing errors',
    });

    // Configure error handling (catch and flag for manual review)
    extractTask.addCatch(flagForManualReview, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });

    matchTask.addCatch(flagForManualReview, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });

    detectTask.addCatch(flagForManualReview, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });

    resolveTask.addCatch(flagForManualReview, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });

    // Define the workflow: Extract → Match → Detect → Resolve
    const definition = extractTask
      .next(matchTask)
      .next(detectTask)
      .next(resolveTask);

    // Create the state machine
    this.invoiceProcessingStateMachine = new sfn.StateMachine(this, 'InvoiceProcessingStateMachine', {
      stateMachineName: 'ReconcileAI-InvoiceProcessing',
      definition,
      timeout: cdk.Duration.minutes(5), // Max 5 minutes per invoice
      tracingEnabled: true, // Enable X-Ray tracing for debugging
    });

    // Output state machine details
    new cdk.CfnOutput(this, 'StateMachineArn', {
      value: this.invoiceProcessingStateMachine.stateMachineArn,
      description: 'Invoice Processing State Machine ARN',
    });

    new cdk.CfnOutput(this, 'StateMachineName', {
      value: this.invoiceProcessingStateMachine.stateMachineName,
      description: 'Invoice Processing State Machine Name',
    });

    // ========================================
    // S3 Trigger for Step Functions
    // ========================================

    // Create a Lambda function to trigger Step Functions on S3 upload
    const s3TriggerLambda = new lambda.Function(this, 'S3TriggerLambda', {
      functionName: 'ReconcileAI-S3Trigger',
      runtime: lambda.Runtime.PYTHON_3_11,
      architecture: lambda.Architecture.ARM_64,
      handler: 'index.lambda_handler',
      code: lambda.Code.fromInline(`
import json
import boto3
import os

sfn_client = boto3.client('stepfunctions')
STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']

def lambda_handler(event, context):
    """Trigger Step Functions execution when PDF is uploaded to S3"""
    for record in event.get('Records', []):
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        # Only process PDFs in the invoices/ folder
        if key.startswith('invoices/') and key.endswith('.pdf'):
            # Start Step Functions execution
            execution_input = {
                's3_bucket': bucket,
                's3_key': key,
                'invoice_id': key.split('/')[-1].replace('.pdf', '')
            }
            
            response = sfn_client.start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                input=json.dumps(execution_input)
            )
            
            print(f"Started execution: {response['executionArn']}")
    
    return {
        'statusCode': 200,
        'body': json.dumps('Step Functions triggered successfully')
    }
      `),
      timeout: cdk.Duration.seconds(10),
      memorySize: 128,
      environment: {
        STATE_MACHINE_ARN: this.invoiceProcessingStateMachine.stateMachineArn,
      },
    });

    // Grant Lambda permission to start Step Functions executions
    this.invoiceProcessingStateMachine.grantStartExecution(s3TriggerLambda);

    // Grant Lambda permission to read from S3
    this.invoiceBucket.grantRead(s3TriggerLambda);

    // Add S3 event notification to trigger Lambda on PDF upload
    this.invoiceBucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(s3TriggerLambda),
      {
        prefix: 'invoices/',
        suffix: '.pdf',
      }
    );

    // Output S3 trigger Lambda details
    new cdk.CfnOutput(this, 'S3TriggerLambdaName', {
      value: s3TriggerLambda.functionName,
      description: 'S3 Trigger Lambda Function Name',
    });

    // ========================================
    // API Gateway REST API with Cognito Authorizer
    // ========================================

    // Create Cognito Authorizer
    const cognitoAuthorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'CognitoAuthorizer', {
      cognitoUserPools: [this.userPool],
      authorizerName: 'ReconcileAI-Authorizer',
      identitySource: 'method.request.header.Authorization',
    });

    // Create REST API
    this.api = new apigateway.RestApi(this, 'ReconcileAIAPI', {
      restApiName: 'ReconcileAI-API',
      description: 'API for ReconcileAI invoice processing system',
      deployOptions: {
        stageName: 'prod',
        tracingEnabled: true, // Enable X-Ray tracing
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
        metricsEnabled: true,
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS, // Configure specific origins in production
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: [
          'Content-Type',
          'X-Amz-Date',
          'Authorization',
          'X-Api-Key',
          'X-Amz-Security-Token',
        ],
        allowCredentials: true,
      },
      cloudWatchRole: true, // Enable CloudWatch logging
    });

    // PO Management Lambda Handler
    this.poManagementLambda = new lambda.Function(this, 'POManagementLambda', {
      functionName: 'ReconcileAI-POManagement',
      runtime: lambda.Runtime.PYTHON_3_11,
      architecture: lambda.Architecture.ARM_64,
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../lambda/po-management')),
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      environment: {
        POS_TABLE_NAME: this.posTable.tableName,
        AUDIT_LOGS_TABLE_NAME: this.auditLogsTable.tableName,
      },
    });

    // Grant permissions
    this.posTable.grantReadWriteData(this.poManagementLambda);
    this.auditLogsTable.grantWriteData(this.poManagementLambda);

    // Invoice Management Lambda Handler
    this.invoiceManagementLambda = new lambda.Function(this, 'InvoiceManagementLambda', {
      functionName: 'ReconcileAI-InvoiceManagement',
      runtime: lambda.Runtime.PYTHON_3_11,
      architecture: lambda.Architecture.ARM_64,
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../lambda/invoice-management')),
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      environment: {
        INVOICES_TABLE_NAME: this.invoicesTable.tableName,
        AUDIT_LOGS_TABLE_NAME: this.auditLogsTable.tableName,
        STATE_MACHINE_ARN: this.invoiceProcessingStateMachine.stateMachineArn,
      },
    });

    // Grant permissions
    this.invoicesTable.grantReadWriteData(this.invoiceManagementLambda);
    this.auditLogsTable.grantWriteData(this.invoiceManagementLambda);
    this.invoiceProcessingStateMachine.grantStartExecution(this.invoiceManagementLambda);
    this.invoiceManagementLambda.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['states:SendTaskSuccess', 'states:SendTaskFailure'],
        resources: [this.invoiceProcessingStateMachine.stateMachineArn],
      })
    );

    // Create API resources and methods

    // /pos resource
    const posResource = this.api.root.addResource('pos');
    
    // POST /pos - Upload PO
    posResource.addMethod(
      'POST',
      new apigateway.LambdaIntegration(this.poManagementLambda, {
        proxy: true,
        integrationResponses: [
          {
            statusCode: '200',
            responseParameters: {
              'method.response.header.Access-Control-Allow-Origin': "'*'",
            },
          },
        ],
      }),
      {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        methodResponses: [
          {
            statusCode: '200',
            responseParameters: {
              'method.response.header.Access-Control-Allow-Origin': true,
            },
          },
        ],
      }
    );

    // GET /pos - Search POs
    posResource.addMethod(
      'GET',
      new apigateway.LambdaIntegration(this.poManagementLambda, {
        proxy: true,
        integrationResponses: [
          {
            statusCode: '200',
            responseParameters: {
              'method.response.header.Access-Control-Allow-Origin': "'*'",
            },
          },
        ],
      }),
      {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        methodResponses: [
          {
            statusCode: '200',
            responseParameters: {
              'method.response.header.Access-Control-Allow-Origin': true,
            },
          },
        ],
      }
    );

    // /invoices resource
    const invoicesResource = this.api.root.addResource('invoices');
    
    // GET /invoices - Query invoices
    invoicesResource.addMethod(
      'GET',
      new apigateway.LambdaIntegration(this.invoiceManagementLambda, {
        proxy: true,
        integrationResponses: [
          {
            statusCode: '200',
            responseParameters: {
              'method.response.header.Access-Control-Allow-Origin': "'*'",
            },
          },
        ],
      }),
      {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        methodResponses: [
          {
            statusCode: '200',
            responseParameters: {
              'method.response.header.Access-Control-Allow-Origin': true,
            },
          },
        ],
      }
    );

    // /invoices/{id} resource
    const invoiceIdResource = invoicesResource.addResource('{id}');

    // POST /invoices/{id}/approve - Approve invoice
    const approveResource = invoiceIdResource.addResource('approve');
    approveResource.addMethod(
      'POST',
      new apigateway.LambdaIntegration(this.invoiceManagementLambda, {
        proxy: true,
        integrationResponses: [
          {
            statusCode: '200',
            responseParameters: {
              'method.response.header.Access-Control-Allow-Origin': "'*'",
            },
          },
        ],
      }),
      {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        methodResponses: [
          {
            statusCode: '200',
            responseParameters: {
              'method.response.header.Access-Control-Allow-Origin': true,
            },
          },
        ],
      }
    );

    // POST /invoices/{id}/reject - Reject invoice
    const rejectResource = invoiceIdResource.addResource('reject');
    rejectResource.addMethod(
      'POST',
      new apigateway.LambdaIntegration(this.invoiceManagementLambda, {
        proxy: true,
        integrationResponses: [
          {
            statusCode: '200',
            responseParameters: {
              'method.response.header.Access-Control-Allow-Origin': "'*'",
            },
          },
        ],
      }),
      {
        authorizer: cognitoAuthorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
        methodResponses: [
          {
            statusCode: '200',
            responseParameters: {
              'method.response.header.Access-Control-Allow-Origin': true,
            },
          },
        ],
      }
    );

    // Output API Gateway details
    new cdk.CfnOutput(this, 'APIGatewayURL', {
      value: this.api.url,
      description: 'API Gateway URL',
    });

    new cdk.CfnOutput(this, 'APIGatewayId', {
      value: this.api.restApiId,
      description: 'API Gateway REST API ID',
    });

    new cdk.CfnOutput(this, 'POManagementLambdaName', {
      value: this.poManagementLambda.functionName,
      description: 'PO Management Lambda Function Name',
    });

    new cdk.CfnOutput(this, 'InvoiceManagementLambdaName', {
      value: this.invoiceManagementLambda.functionName,
      description: 'Invoice Management Lambda Function Name',
    });
  }
}
