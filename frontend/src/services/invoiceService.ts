// Invoice Service for API interactions
import { Invoice, InvoiceFilter, InvoiceDetail } from '../types/invoice';

const API_ENDPOINT = process.env.REACT_APP_API_ENDPOINT || 'http://localhost:3001/api';

export class InvoiceService {
  /**
   * Get invoices with optional filtering
   */
  static async getInvoices(filter: InvoiceFilter = {}): Promise<Invoice[]> {
    try {
      const params = new URLSearchParams();
      if (filter.status) params.append('status', filter.status);
      if (filter.vendorName) params.append('vendorName', filter.vendorName);
      if (filter.dateFrom) params.append('dateFrom', filter.dateFrom);
      if (filter.dateTo) params.append('dateTo', filter.dateTo);

      const response = await fetch(`${API_ENDPOINT}/invoices?${params.toString()}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch invoices');
      }

      const data = await response.json();
      return data.invoices || [];
    } catch (error) {
      console.error('Error fetching invoices:', error);
      throw error;
    }
  }

  /**
   * Get a single invoice by ID with full details
   */
  static async getInvoiceById(invoiceId: string): Promise<InvoiceDetail | null> {
    try {
      const response = await fetch(`${API_ENDPOINT}/invoices/${invoiceId}`);
      
      if (!response.ok) {
        if (response.status === 404) {
          return null;
        }
        throw new Error('Failed to fetch invoice details');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching invoice details:', error);
      throw error;
    }
  }

  /**
   * Approve an invoice
   */
  static async approveInvoice(invoiceId: string, comment: string, userId: string): Promise<void> {
    try {
      const response = await fetch(`${API_ENDPOINT}/invoices/${invoiceId}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          comment,
          approverId: userId
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to approve invoice');
      }
    } catch (error) {
      console.error('Error approving invoice:', error);
      throw error;
    }
  }

  /**
   * Reject an invoice
   */
  static async rejectInvoice(invoiceId: string, reason: string, userId: string): Promise<void> {
    try {
      const response = await fetch(`${API_ENDPOINT}/invoices/${invoiceId}/reject`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          reason,
          approverId: userId
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to reject invoice');
      }
    } catch (error) {
      console.error('Error rejecting invoice:', error);
      throw error;
    }
  }
}
