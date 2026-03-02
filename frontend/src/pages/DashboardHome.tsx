import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { InvoiceService } from '../services/invoiceService';
import { POService } from '../services/poService';
import { Invoice, InvoiceStatus } from '../types/invoice';
import './DashboardHome.css';

interface DashboardStats {
  totalInvoices: number;
  pendingApprovals: number;
  autoApproved: number;
  totalPOs: number;
  processingInvoices: number;
  rejectedInvoices: number;
}

const DashboardHome: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats>({
    totalInvoices: 0,
    pendingApprovals: 0,
    autoApproved: 0,
    totalPOs: 0,
    processingInvoices: 0,
    rejectedInvoices: 0
  });
  const [recentInvoices, setRecentInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);

      // Load invoices
      const allInvoices = await InvoiceService.getInvoices({});
      const flaggedInvoices = allInvoices.filter(inv => inv.Status === InvoiceStatus.FLAGGED);
      const approvedInvoices = allInvoices.filter(inv => inv.Status === InvoiceStatus.APPROVED);
      const processingInvoices = allInvoices.filter(inv =>
        inv.Status === InvoiceStatus.RECEIVED ||
        inv.Status === InvoiceStatus.EXTRACTING ||
        inv.Status === InvoiceStatus.MATCHING ||
        inv.Status === InvoiceStatus.DETECTING
      );
      const rejectedInvoices = allInvoices.filter(inv => inv.Status === InvoiceStatus.REJECTED);

      // Load POs
      const allPOs = await POService.searchPOs({});

      setStats({
        totalInvoices: allInvoices.length,
        pendingApprovals: flaggedInvoices.length,
        autoApproved: approvedInvoices.length,
        totalPOs: allPOs.length,
        processingInvoices: processingInvoices.length,
        rejectedInvoices: rejectedInvoices.length
      });

      // Get 5 most recent invoices
      const sorted = [...allInvoices].sort((a, b) =>
        new Date(b.ReceivedDate).getTime() - new Date(a.ReceivedDate).getTime()
      );
      setRecentInvoices(sorted.slice(0, 5));

    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadgeClass = (status: InvoiceStatus): string => {
    switch (status) {
      case InvoiceStatus.APPROVED:
        return 'status-badge status-approved';
      case InvoiceStatus.FLAGGED:
        return 'status-badge status-flagged';
      case InvoiceStatus.REJECTED:
        return 'status-badge status-rejected';
      case InvoiceStatus.RECEIVED:
      case InvoiceStatus.EXTRACTING:
      case InvoiceStatus.MATCHING:
      case InvoiceStatus.DETECTING:
        return 'status-badge status-processing';
      default:
        return 'status-badge';
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const formatCurrency = (amount: number | string): string => {
    const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(numAmount);
  };

  if (loading) {
    return (
      <div className="dashboard-home">
        <div className="loading-spinner">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="dashboard-home">
      <div className="dashboard-header">
        <div>
          <h1>Dashboard</h1>
          <p className="dashboard-subtitle">Welcome to ReconcileAI - Autonomous Accounts Payable</p>
        </div>
        <button className="btn-refresh" onClick={loadDashboardData}>
          <span>↻</span> Refresh
        </button>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card stat-card-primary" onClick={() => navigate('/invoices')}>
          <div className="stat-icon">📄</div>
          <div className="stat-content">
            <div className="stat-value">{stats.totalInvoices}</div>
            <div className="stat-label">Total Invoices</div>
          </div>
        </div>

        <div className="stat-card stat-card-warning" onClick={() => navigate('/invoices')}>
          <div className="stat-icon">⚠️</div>
          <div className="stat-content">
            <div className="stat-value">{stats.pendingApprovals}</div>
            <div className="stat-label">Pending Approvals</div>
          </div>
        </div>

        <div className="stat-card stat-card-success" onClick={() => navigate('/invoices')}>
          <div className="stat-icon">✓</div>
          <div className="stat-content">
            <div className="stat-value">{stats.autoApproved}</div>
            <div className="stat-label">Auto-Approved</div>
          </div>
        </div>

        <div className="stat-card stat-card-info" onClick={() => navigate('/pos')}>
          <div className="stat-icon">📋</div>
          <div className="stat-content">
            <div className="stat-value">{stats.totalPOs}</div>
            <div className="stat-label">Purchase Orders</div>
          </div>
        </div>

        <div className="stat-card stat-card-processing">
          <div className="stat-icon">⚙️</div>
          <div className="stat-content">
            <div className="stat-value">{stats.processingInvoices}</div>
            <div className="stat-label">Processing</div>
          </div>
        </div>

        <div className="stat-card stat-card-danger">
          <div className="stat-icon">✗</div>
          <div className="stat-content">
            <div className="stat-value">{stats.rejectedInvoices}</div>
            <div className="stat-label">Rejected</div>
          </div>
        </div>
      </div>

      {/* Recent Invoices */}
      <div className="dashboard-section">
        <div className="section-header">
          <h2>Recent Invoices</h2>
          <button className="btn-link" onClick={() => navigate('/invoices')}>
            View All →
          </button>
        </div>

        {recentInvoices.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📭</div>
            <h3>No Invoices Yet</h3>
            <p>Invoices will appear here once they are received via email</p>
            <button className="btn-primary" onClick={() => navigate('/pos')}>
              Upload Purchase Orders First
            </button>
          </div>
        ) : (
          <div className="invoices-table-container">
            <table className="invoices-table">
              <thead>
                <tr>
                  <th>Invoice #</th>
                  <th>Vendor</th>
                  <th>Amount</th>
                  <th>Date</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {recentInvoices.map(invoice => (
                  <tr key={invoice.InvoiceId}>
                    <td className="invoice-number">{invoice.InvoiceNumber}</td>
                    <td>{invoice.VendorName}</td>
                    <td className="amount">{formatCurrency(invoice.TotalAmount)}</td>
                    <td>{formatDate(invoice.ReceivedDate)}</td>
                    <td>
                      <span className={getStatusBadgeClass(invoice.Status)}>
                        {invoice.Status}
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn-view"
                        onClick={() => navigate('/invoices')}
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="dashboard-section">
        <h2>Quick Actions</h2>
        <div className="quick-actions">
          <button className="action-card" onClick={() => navigate('/pos')}>
            <div className="action-icon">📤</div>
            <div className="action-title">Upload PO</div>
            <div className="action-description">Add new purchase orders</div>
          </button>

          <button className="action-card" onClick={() => navigate('/invoices')}>
            <div className="action-icon">🔍</div>
            <div className="action-title">Review Invoices</div>
            <div className="action-description">Check pending approvals</div>
          </button>

          <button className="action-card" onClick={() => navigate('/audit')}>
            <div className="action-icon">📊</div>
            <div className="action-title">Audit Trail</div>
            <div className="action-description">View system activity</div>
          </button>
        </div>
      </div>
    </div>
  );
};

export default DashboardHome;
