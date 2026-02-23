import React from 'react';
import './DashboardHome.css';

const DashboardHome: React.FC = () => {
  return (
    <div className="dashboard-home">
      <h1>Dashboard</h1>
      <p>Welcome to ReconcileAI - Autonomous Accounts Payable Clerk</p>
      <div className="dashboard-cards">
        <div className="dashboard-card">
          <h3>Recent Invoices</h3>
          <p>View and manage incoming invoices</p>
        </div>
        <div className="dashboard-card">
          <h3>Purchase Orders</h3>
          <p>Upload and search purchase orders</p>
        </div>
        <div className="dashboard-card">
          <h3>Pending Approvals</h3>
          <p>Review flagged invoices requiring approval</p>
        </div>
      </div>
    </div>
  );
};

export default DashboardHome;
