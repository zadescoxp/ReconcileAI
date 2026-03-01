import React, { useState, useEffect } from 'react';
import { Invoice, InvoiceStatus, InvoiceFilter } from '../types/invoice';
import { InvoiceService } from '../services/invoiceService';
import './InvoiceList.css';

interface InvoiceListProps {
  onInvoiceClick: (invoiceId: string) => void;
}

const InvoiceList: React.FC<InvoiceListProps> = ({ onInvoiceClick }) => {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | 'All'>('All');

  useEffect(() => {
    loadInvoices();
  }, [statusFilter]);

  const loadInvoices = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const filter: InvoiceFilter = {};
      if (statusFilter !== 'All') {
        filter.status = statusFilter;
      }

      const data = await InvoiceService.getInvoices(filter);
      setInvoices(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadgeClass = (status: InvoiceStatus): string => {
    switch (status) {
      case InvoiceStatus.APPROVED:
        return 'status-badge status-approved';
      case InvoiceStatus.REJECTED:
        return 'status-badge status-rejected';
      case InvoiceStatus.FLAGGED:
        return 'status-badge status-flagged';
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
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return dateString;
    }
  };

  const formatCurrency = (amount: number | string): string => {
    const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(numAmount);
  };

  if (loading) {
    return <div className="invoice-list-loading">Loading invoices...</div>;
  }

  if (error) {
    return (
      <div className="invoice-list-error">
        <p>Error loading invoices: {error}</p>
        <button onClick={loadInvoices}>Retry</button>
      </div>
    );
  }

  return (
    <div className="invoice-list-container">
      <div className="invoice-list-header">
        <h2>Invoices</h2>
        <div className="invoice-list-filters">
          <label htmlFor="status-filter">Filter by Status:</label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as InvoiceStatus | 'All')}
          >
            <option value="All">All</option>
            <option value={InvoiceStatus.FLAGGED}>Flagged</option>
            <option value={InvoiceStatus.APPROVED}>Approved</option>
            <option value={InvoiceStatus.REJECTED}>Rejected</option>
            <option value={InvoiceStatus.RECEIVED}>Received</option>
            <option value={InvoiceStatus.EXTRACTING}>Extracting</option>
            <option value={InvoiceStatus.MATCHING}>Matching</option>
            <option value={InvoiceStatus.DETECTING}>Detecting</option>
          </select>
        </div>
      </div>

      {invoices.length === 0 ? (
        <div className="invoice-list-empty">
          <p>No invoices found</p>
        </div>
      ) : (
        <div className="invoice-list-table-container">
          <table className="invoice-list-table">
            <thead>
              <tr>
                <th>Invoice Number</th>
                <th>Vendor</th>
                <th>Date</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Flags</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((invoice) => (
                <tr key={invoice.InvoiceId}>
                  <td>{invoice.InvoiceNumber}</td>
                  <td>{invoice.VendorName}</td>
                  <td>{formatDate(invoice.InvoiceDate)}</td>
                  <td>{formatCurrency(invoice.TotalAmount)}</td>
                  <td>
                    <span className={getStatusBadgeClass(invoice.Status)}>
                      {invoice.Status}
                    </span>
                  </td>
                  <td>
                    {invoice.Discrepancies.length > 0 && (
                      <span className="flag-indicator discrepancy">
                        {invoice.Discrepancies.length} Discrepancy
                      </span>
                    )}
                    {invoice.FraudFlags.length > 0 && (
                      <span className="flag-indicator fraud">
                        {invoice.FraudFlags.length} Fraud
                      </span>
                    )}
                  </td>
                  <td>
                    <button
                      className="btn-view-details"
                      onClick={() => onInvoiceClick(invoice.InvoiceId)}
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default InvoiceList;
