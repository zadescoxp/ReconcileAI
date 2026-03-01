import React, { useState, useEffect } from 'react';
import { InvoiceDetail as InvoiceDetailType, DiscrepancyType, Severity, InvoiceStatus } from '../types/invoice';
import { InvoiceService } from '../services/invoiceService';
import { useAuth } from '../contexts/AuthContext';
import './InvoiceDetail.css';

interface InvoiceDetailProps {
  invoiceId: string;
  onBack: () => void;
}

const InvoiceDetail: React.FC<InvoiceDetailProps> = ({ invoiceId, onBack }) => {
  const [invoiceDetail, setInvoiceDetail] = useState<InvoiceDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showReasoning, setShowReasoning] = useState(false);
  const [comment, setComment] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const { user } = useAuth();

  useEffect(() => {
    loadInvoiceDetail();
  }, [invoiceId]);

  const loadInvoiceDetail = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await InvoiceService.getInvoiceById(invoiceId);
      setInvoiceDetail(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
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

  const getDiscrepancyTypeLabel = (type: DiscrepancyType): string => {
    switch (type) {
      case DiscrepancyType.PRICE_MISMATCH:
        return 'Price Mismatch';
      case DiscrepancyType.QUANTITY_MISMATCH:
        return 'Quantity Mismatch';
      case DiscrepancyType.ITEM_NOT_FOUND:
        return 'Item Not Found';
      case DiscrepancyType.AMOUNT_EXCEEDED:
        return 'Amount Exceeded';
      default:
        return type;
    }
  };

  const getSeverityClass = (severity: Severity): string => {
    switch (severity) {
      case Severity.HIGH:
        return 'severity-high';
      case Severity.MEDIUM:
        return 'severity-medium';
      case Severity.LOW:
        return 'severity-low';
      default:
        return '';
    }
  };

  const handleApprove = async () => {
    if (!user) {
      setActionError('User not authenticated');
      return;
    }

    try {
      setActionLoading(true);
      setActionError(null);
      setActionSuccess(null);

      await InvoiceService.approveInvoice(invoiceId, comment, user.userId);
      
      setActionSuccess('Invoice approved successfully');
      setComment('');
      
      // Reload invoice details to show updated status
      setTimeout(() => {
        loadInvoiceDetail();
      }, 1000);
    } catch (err) {
      setActionError((err as Error).message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!user) {
      setActionError('User not authenticated');
      return;
    }

    if (!comment.trim()) {
      setActionError('Please provide a reason for rejection');
      return;
    }

    try {
      setActionLoading(true);
      setActionError(null);
      setActionSuccess(null);

      await InvoiceService.rejectInvoice(invoiceId, comment, user.userId);
      
      setActionSuccess('Invoice rejected successfully');
      setComment('');
      
      // Reload invoice details to show updated status
      setTimeout(() => {
        loadInvoiceDetail();
      }, 1000);
    } catch (err) {
      setActionError((err as Error).message);
    } finally {
      setActionLoading(false);
    }
  };

  const canTakeAction = (): boolean => {
    return invoiceDetail?.invoice.Status === InvoiceStatus.FLAGGED;
  };

  if (loading) {
    return <div className="invoice-detail-loading">Loading invoice details...</div>;
  }

  if (error || !invoiceDetail) {
    return (
      <div className="invoice-detail-error">
        <p>Error loading invoice details: {error || 'Invoice not found'}</p>
        <button onClick={onBack}>Back to List</button>
      </div>
    );
  }

  const { invoice, matchedPOs } = invoiceDetail;

  return (
    <div className="invoice-detail-container">
      <div className="invoice-detail-header">
        <button className="btn-back" onClick={onBack}>
          ← Back to List
        </button>
        <h2>Invoice Details</h2>
      </div>

      <div className="invoice-detail-content">
        {/* Invoice Information */}
        <div className="detail-section">
          <h3>Invoice Information</h3>
          <div className="detail-grid">
            <div className="detail-item">
              <label>Invoice Number:</label>
              <span>{invoice.InvoiceNumber}</span>
            </div>
            <div className="detail-item">
              <label>Vendor:</label>
              <span>{invoice.VendorName}</span>
            </div>
            <div className="detail-item">
              <label>Invoice Date:</label>
              <span>{formatDate(invoice.InvoiceDate)}</span>
            </div>
            <div className="detail-item">
              <label>Total Amount:</label>
              <span className="amount">{formatCurrency(invoice.TotalAmount)}</span>
            </div>
            <div className="detail-item">
              <label>Status:</label>
              <span className={`status-badge status-${invoice.Status.toLowerCase()}`}>
                {invoice.Status}
              </span>
            </div>
            <div className="detail-item">
              <label>Received Date:</label>
              <span>{formatDate(invoice.ReceivedDate)}</span>
            </div>
          </div>
        </div>

        {/* Invoice Line Items */}
        <div className="detail-section">
          <h3>Invoice Line Items</h3>
          <table className="line-items-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Description</th>
                <th>Quantity</th>
                <th>Unit Price</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {invoice.LineItems.map((item) => (
                <tr key={item.LineNumber}>
                  <td>{item.LineNumber}</td>
                  <td>{item.ItemDescription}</td>
                  <td>{item.Quantity}</td>
                  <td>{formatCurrency(item.UnitPrice)}</td>
                  <td>{formatCurrency(item.TotalPrice)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Matched POs */}
        {matchedPOs && matchedPOs.length > 0 && (
          <div className="detail-section">
            <h3>Matched Purchase Orders</h3>
            {matchedPOs.map((po) => (
              <div key={po.POId} className="matched-po">
                <div className="po-header">
                  <strong>PO #{po.PONumber}</strong>
                  <span>Total: {formatCurrency(po.TotalAmount)}</span>
                </div>
                <table className="line-items-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Description</th>
                      <th>Quantity</th>
                      <th>Unit Price</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {po.LineItems.map((item: any) => (
                      <tr key={item.LineNumber}>
                        <td>{item.LineNumber}</td>
                        <td>{item.ItemDescription}</td>
                        <td>{item.Quantity}</td>
                        <td>{formatCurrency(item.UnitPrice)}</td>
                        <td>{formatCurrency(item.TotalPrice)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        )}

        {/* Discrepancies */}
        {invoice.Discrepancies && invoice.Discrepancies.length > 0 && (
          <div className="detail-section discrepancies-section">
            <h3>Discrepancies ({invoice.Discrepancies.length})</h3>
            {invoice.Discrepancies.map((discrepancy, index) => (
              <div key={index} className="discrepancy-item">
                <div className="discrepancy-header">
                  <span className="discrepancy-type">
                    {getDiscrepancyTypeLabel(discrepancy.type)}
                  </span>
                  <span className="discrepancy-difference">
                    Difference: {formatCurrency(Math.abs(discrepancy.difference))}
                  </span>
                </div>
                <p className="discrepancy-description">{discrepancy.description}</p>
                <div className="discrepancy-comparison">
                  <div className="comparison-item">
                    <strong>Invoice Line:</strong>
                    <p>{discrepancy.invoiceLine.ItemDescription}</p>
                    <p>Qty: {discrepancy.invoiceLine.Quantity} @ {formatCurrency(discrepancy.invoiceLine.UnitPrice)}</p>
                  </div>
                  <div className="comparison-item">
                    <strong>PO Line:</strong>
                    <p>{discrepancy.poLine.ItemDescription}</p>
                    <p>Qty: {discrepancy.poLine.Quantity} @ {formatCurrency(discrepancy.poLine.UnitPrice)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Fraud Flags */}
        {invoice.FraudFlags && invoice.FraudFlags.length > 0 && (
          <div className="detail-section fraud-flags-section">
            <h3>Fraud Flags ({invoice.FraudFlags.length})</h3>
            {invoice.FraudFlags.map((flag, index) => (
              <div key={index} className={`fraud-flag-item ${getSeverityClass(flag.severity)}`}>
                <div className="fraud-flag-header">
                  <span className="fraud-flag-type">{flag.flagType.replace(/_/g, ' ')}</span>
                  <span className={`severity-badge ${getSeverityClass(flag.severity)}`}>
                    {flag.severity}
                  </span>
                </div>
                <p className="fraud-flag-description">{flag.description}</p>
                {flag.evidence && Object.keys(flag.evidence).length > 0 && (
                  <div className="fraud-flag-evidence">
                    <strong>Evidence:</strong>
                    <pre>{JSON.stringify(flag.evidence, null, 2)}</pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* AI Reasoning */}
        {invoice.AIReasoning && (
          <div className="detail-section ai-reasoning-section">
            <div className="ai-reasoning-header" onClick={() => setShowReasoning(!showReasoning)}>
              <h3>AI Reasoning</h3>
              <button className="btn-toggle">
                {showReasoning ? '▼' : '▶'}
              </button>
            </div>
            {showReasoning && (
              <div className="ai-reasoning-content">
                <pre>{invoice.AIReasoning}</pre>
              </div>
            )}
          </div>
        )}

        {/* Approval Actions */}
        {canTakeAction() && (
          <div className="detail-section approval-actions-section">
            <h3>Approval Actions</h3>
            
            {actionSuccess && (
              <div className="action-message action-success">
                {actionSuccess}
              </div>
            )}
            
            {actionError && (
              <div className="action-message action-error">
                {actionError}
              </div>
            )}

            <div className="approval-form">
              <div className="form-group">
                <label htmlFor="comment">Comment / Reason:</label>
                <textarea
                  id="comment"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Add a comment or reason for your decision..."
                  rows={4}
                  disabled={actionLoading}
                />
              </div>

              <div className="approval-buttons">
                <button
                  className="btn-approve"
                  onClick={handleApprove}
                  disabled={actionLoading}
                >
                  {actionLoading ? 'Processing...' : 'Approve Invoice'}
                </button>
                <button
                  className="btn-reject"
                  onClick={handleReject}
                  disabled={actionLoading || !comment.trim()}
                >
                  {actionLoading ? 'Processing...' : 'Reject Invoice'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default InvoiceDetail;
