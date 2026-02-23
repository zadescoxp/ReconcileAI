// AWS Amplify configuration
// This will be populated with actual values from CDK deployment
const awsconfig = {
  Auth: {
    Cognito: {
      userPoolId: process.env.REACT_APP_USER_POOL_ID || '',
      userPoolClientId: process.env.REACT_APP_USER_POOL_CLIENT_ID || '',
      region: process.env.REACT_APP_AWS_REGION || 'us-east-1',
    }
  },
  API: {
    REST: {
      ReconcileAPI: {
        endpoint: process.env.REACT_APP_API_ENDPOINT || '',
        region: process.env.REACT_APP_AWS_REGION || 'us-east-1',
      }
    }
  }
};

export default awsconfig;
