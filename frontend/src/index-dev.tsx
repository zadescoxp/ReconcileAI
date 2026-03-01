import ReactDOM from 'react-dom/client';
import './index.css';
import DevApp from './DevApp';
import reportWebVitals from './reportWebVitals';

/**
 * Development entry point - runs the app without AWS authentication
 * 
 * To use this:
 * 1. Temporarily rename src/index.tsx to src/index-prod.tsx
 * 2. Rename this file to src/index.tsx
 * 3. Run: npm start
 */

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <DevApp />
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
