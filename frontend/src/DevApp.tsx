import { useState } from 'react';
import { Role } from './types/auth';
import './App.css';

/**
 * Development App - Simple UI preview without AWS authentication
 * 
 * This is a standalone version for local development and UI preview.
 * Shows a simplified version of the dashboard.
 */
function DevApp() {
  const [currentView, setCurrentView] = useState<string>('dashboard');

  return (
    <div className="dev-app">
      <div className="dev-banner">
        🔧 Development Mode - No AWS Connection Required
      </div>
      
      <div className="dev-container">
        <div className="dev-header">
          <h1>ReconcileAI Dashboard</h1>
          <div className="dev-user-info">
            <span>👤 Dev User (Admin)</span>
          </div>
        </div>

        <div className="dev-nav">
          <button 
            className={currentView === 'dashboard' ? 'active' : ''}
            onClick={() => setCurrentView('dashboard')}
          >
            📊 Dashboard
          </button>
          <button 
            className={currentView === 'po-upload' ? 'active' : ''}
            onClick={() => setCurrentView('po-upload')}
          >
            📤 Upload PO
          </button>
          <button 
            className={currentView === 'invoices' ? 'active' : ''}
            onClick={() => setCurrentView('invoices')}
          >
            📄 Invoices
          </button>
          <button 
            className={currentView === 'audit' ? 'active' : ''}
            onClick={() => setCurrentView('audit')}
          >
            📋 Audit Trail
          </button>
        </div>

        <div className="dev-content">
          {currentView === 'dashboard' && (
            <div className="dev-section">
              <h2>Dashboard Overview</h2>
              <div className="dev-stats">
                <div className="stat-card">
                  <h3>Total Invoices</h3>
                  <p className="stat-number">24</p>
                  <p className="stat-label">This Month</p>
                </div>
                <div className="stat-card">
                  <h3>Pending Review</h3>
                  <p className="stat-number">3</p>
                  <p className="stat-label">Awaiting Approval</p>
                </div>
                <div className="stat-card">
                  <h3>Auto-Approved</h3>
                  <p className="stat-number">18</p>
                  <p className="stat-label">Perfect Matches</p>
                </div>
                <div className="stat-card">
                  <h3>Fraud Flags</h3>
                  <p className="stat-number">2</p>
                  <p className="stat-label">Requires Investigation</p>
                </div>
              </div>
              <div className="dev-info">
                <p>✅ All components are working</p>
                <p>✅ UI is responsive and styled</p>
                <p>✅ Ready for AWS deployment</p>
              </div>
            </div>
          )}

          {currentView === 'po-upload' && (
            <div className="dev-section">
              <h2>Upload Purchase Order</h2>
              <div className="upload-area">
                <p>📁 Drag and drop CSV or JSON file here</p>
                <p>or</p>
                <button className="upload-button">Choose File</button>
              </div>
              <div className="dev-info">
                <p>In production, this uploads POs to DynamoDB</p>
              </div>
            </div>
          )}

          {currentView === 'invoices' && (
            <div className="dev-section">
              <h2>Invoice List</h2>
              <table className="dev-table">
                <thead>
                  <tr>
                    <th>Invoice #</th>
                    <th>Vendor</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>INV-2024-001</td>
                    <td>TechSupplies Inc</td>
                    <td>$6,250.00</td>
                    <td><span className="status-approved">Approved</span></td>
                    <td>2024-02-20</td>
                  </tr>
                  <tr>
                    <td>INV-2024-002</td>
                    <td>Office Depot Pro</td>
                    <td>$7,150.00</td>
                    <td><span className="status-flagged">Flagged</span></td>
                    <td>2024-02-21</td>
                  </tr>
                  <tr>
                    <td>INV-2024-003</td>
                    <td>Acme Supplies</td>
                    <td>$550.00</td>
                    <td><span className="status-fraud">Fraud Alert</span></td>
                    <td>2024-02-22</td>
                  </tr>
                </tbody>
              </table>
              <div className="dev-info">
                <p>In production, this queries DynamoDB for real invoices</p>
              </div>
            </div>
          )}

          {currentView === 'audit' && (
            <div className="dev-section">
              <h2>Audit Trail</h2>
              <div className="audit-log">
                <div className="log-entry">
                  <span className="log-time">2024-02-24 10:30:15</span>
                  <span className="log-action">Invoice Approved</span>
                  <span className="log-user">admin@example.com</span>
                  <span className="log-entity">INV-2024-001</span>
                </div>
                <div className="log-entry">
                  <span className="log-time">2024-02-24 10:25:42</span>
                  <span className="log-action">AI Matching Complete</span>
                  <span className="log-user">System</span>
                  <span className="log-entity">INV-2024-001</span>
                </div>
                <div className="log-entry">
                  <span className="log-time">2024-02-24 10:25:10</span>
                  <span className="log-action">Invoice Received</span>
                  <span className="log-user">System</span>
                  <span className="log-entity">INV-2024-001</span>
                </div>
              </div>
              <div className="dev-info">
                <p>In production, this shows comprehensive audit logs from DynamoDB</p>
              </div>
            </div>
          )}
        </div>
      </div>

      <style>{`
        .dev-banner {
          background: #ff9800;
          color: white;
          padding: 12px;
          text-align: center;
          font-weight: bold;
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          z-index: 10000;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .dev-app {
          padding-top: 48px;
          min-height: 100vh;
          background: #f5f5f5;
        }

        .dev-container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
        }

        .dev-header {
          background: white;
          padding: 20px;
          border-radius: 8px;
          margin-bottom: 20px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .dev-header h1 {
          margin: 0;
          color: #1976d2;
        }

        .dev-user-info {
          font-size: 14px;
          color: #666;
        }

        .dev-nav {
          background: white;
          padding: 15px;
          margin-bottom: 20px;
          border-radius: 8px;
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .dev-nav button {
          padding: 10px 20px;
          background: #e3f2fd;
          color: #1976d2;
          border: 2px solid transparent;
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          transition: all 0.2s;
        }

        .dev-nav button:hover {
          background: #bbdefb;
        }

        .dev-nav button.active {
          background: #1976d2;
          color: white;
          border-color: #1565c0;
        }

        .dev-content {
          background: white;
          padding: 30px;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .dev-section h2 {
          margin-top: 0;
          color: #333;
          border-bottom: 2px solid #1976d2;
          padding-bottom: 10px;
        }

        .dev-stats {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 20px;
          margin: 20px 0;
        }

        .stat-card {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 20px;
          border-radius: 8px;
          text-align: center;
        }

        .stat-card h3 {
          margin: 0 0 10px 0;
          font-size: 14px;
          opacity: 0.9;
        }

        .stat-number {
          font-size: 36px;
          font-weight: bold;
          margin: 10px 0;
        }

        .stat-label {
          font-size: 12px;
          opacity: 0.8;
          margin: 0;
        }

        .dev-info {
          background: #e8f5e9;
          border-left: 4px solid #4caf50;
          padding: 15px;
          margin-top: 20px;
          border-radius: 4px;
        }

        .dev-info p {
          margin: 5px 0;
          color: #2e7d32;
        }

        .upload-area {
          border: 2px dashed #1976d2;
          border-radius: 8px;
          padding: 60px;
          text-align: center;
          background: #f5f5f5;
          margin: 20px 0;
        }

        .upload-button {
          background: #1976d2;
          color: white;
          border: none;
          padding: 12px 24px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 16px;
          margin-top: 10px;
        }

        .upload-button:hover {
          background: #1565c0;
        }

        .dev-table {
          width: 100%;
          border-collapse: collapse;
          margin: 20px 0;
        }

        .dev-table th,
        .dev-table td {
          padding: 12px;
          text-align: left;
          border-bottom: 1px solid #ddd;
        }

        .dev-table th {
          background: #f5f5f5;
          font-weight: 600;
          color: #333;
        }

        .dev-table tr:hover {
          background: #f9f9f9;
        }

        .status-approved {
          background: #4caf50;
          color: white;
          padding: 4px 12px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 500;
        }

        .status-flagged {
          background: #ff9800;
          color: white;
          padding: 4px 12px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 500;
        }

        .status-fraud {
          background: #f44336;
          color: white;
          padding: 4px 12px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 500;
        }

        .audit-log {
          margin: 20px 0;
        }

        .log-entry {
          display: grid;
          grid-template-columns: 180px 200px 200px 1fr;
          gap: 15px;
          padding: 12px;
          border-bottom: 1px solid #eee;
          font-size: 14px;
        }

        .log-entry:hover {
          background: #f9f9f9;
        }

        .log-time {
          color: #666;
          font-family: monospace;
        }

        .log-action {
          font-weight: 500;
          color: #1976d2;
        }

        .log-user {
          color: #666;
        }

        .log-entity {
          color: #333;
          font-family: monospace;
        }
      `}</style>
    </div>
  );
}

export default DevApp;
