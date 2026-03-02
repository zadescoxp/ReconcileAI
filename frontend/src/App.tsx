import React from 'react';
import { Amplify } from 'aws-amplify';
import awsconfig from './aws-exports';
import './App.css';
import AuthenticatedApp from './components/AuthenticatedApp';
import { ToastProvider } from './contexts/ToastContext';

// Configure Amplify
Amplify.configure(awsconfig);

function App() {
  return (
    <div className="App">
      <ToastProvider>
        <AuthenticatedApp />
      </ToastProvider>
    </div>
  );
}

export default App;
