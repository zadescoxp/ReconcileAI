import React from 'react';
import { Amplify } from 'aws-amplify';
import awsconfig from './aws-exports';
import './App.css';
import AuthenticatedApp from './components/AuthenticatedApp';

// Configure Amplify
Amplify.configure(awsconfig);

function App() {
  return (
    <div className="App">
      <AuthenticatedApp />
    </div>
  );
}

export default App;
