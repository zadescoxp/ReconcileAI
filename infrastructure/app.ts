#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { ReconcileAIStack } from './stacks/reconcile-ai-stack';

const app = new cdk.App();

// Get environment configuration from context
const environment = app.node.tryGetContext('reconcileai:environment') || 'dev';
const region = app.node.tryGetContext('reconcileai:region') || 'us-east-1';

// Create the main stack
new ReconcileAIStack(app, `ReconcileAI-${environment}`, {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: region,
  },
  description: 'ReconcileAI - Autonomous Accounts Payable Clerk (AWS Free Tier)',
  tags: {
    Project: 'ReconcileAI',
    Environment: environment,
    ManagedBy: 'CDK',
  },
});

app.synth();
