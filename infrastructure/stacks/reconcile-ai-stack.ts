import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as ses from 'aws-cdk-lib/aws-ses';
import * as sesActions from 'aws-cdk-lib/aws-ses-actions';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
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
  }
}
