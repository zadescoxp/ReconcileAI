# ReconcileAI Frontend

React + TypeScript frontend for ReconcileAI, hosted on AWS Amplify.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Copy `.env.example` to `.env` and fill in AWS configuration values from CDK deployment

3. Start development server:
```bash
npm start
```

## Build

```bash
npm run build
```

## Test

```bash
npm test
```

## AWS Amplify Deployment

The frontend is configured for AWS Amplify hosting. After CDK deployment, configure Amplify with:
- Build command: `npm run build`
- Build output directory: `build`
- Environment variables from `.env.example`
