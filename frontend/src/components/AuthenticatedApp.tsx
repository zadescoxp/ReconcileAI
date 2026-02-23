import React from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import { AuthProvider } from '../contexts/AuthContext';
import Dashboard from './Dashboard';

const AuthenticatedApp: React.FC = () => {
  return (
    <Authenticator>
      {({ signOut, user }) => (
        <AuthProvider>
          <Dashboard />
        </AuthProvider>
      )}
    </Authenticator>
  );
};

export default AuthenticatedApp;
