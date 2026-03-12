// Invoice Service for API interactions
import { Invoice, InvoiceFilter } from '../types/invoice';
import { LineItem } from '../types/po';
import { fetchAuthSession } from 'aws-amplify/auth';

const API_ENDPOINT = process.env.REACT_APP_API_ENDPOINT || 'http://localhost:3001/api';

export interface InvoiceMetadata {
  vendorName: string;
  invoiceNumber: string;
  totalAmount: number;
  lineItems: LineItem[];
}

export interface InvoiceUploadResult {
  success: boolean;
  invoiceId?: string;
  message: string;
  errors?: string[];
}

/**
 * Get authentication headers with Cognito token
 */
async function getAuthHeaders(): Promise<HeadersInit> {
  try {
    const session = await fetchAuthSession();
    const idToken = session.tokens?.idToken?.toString();

    if (idToken) {
      return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`
      };
    }

    return {
      'Content-Type': 'application/json'
    };
  } catch (error) {
    console.error('Error getting auth token:', error);
    return {
      'Content-Type': 'application/json'
    };
  }
}

export class InvoiceService {
  /**
   * Upload an invoice to the backend
   */
  static async uploadInvoice(metadata: InvoiceMetadata, userId: string): Promise<InvoiceUploadResult> {
    try {
      // Validate invoice data
      const validationErrors = this.validateInvoice(metadata);
      if (validationErrors.length > 0) {
        return {
          success: false,
          message: 'Invoice validation failed',
          errors: validationErrors
        };
      }

      const headers = await getAuthHeaders();
      const response = await fetch(`${API_ENDPOINT}/invoices`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          ...metadata,
          uploadedBy: userId
        })
      });

      if (!response.ok) {
        const error = await response.json();
        return {
          success: false,
          message: error.message || 'Failed to upload invoice',
          errors: error.errors
        };
      }

      const result = await response.json();
      return {
        success: true,
        invoiceId: result.invoiceId,
        message: 'Invoice uploaded successfully'
      };
    } catch (error) {
      console.error('Error uploading invoice:', error);
      return {
        success: false,
        message: 'Network error: Unable to connect to server',
        errors: [(error as Error).message]
      };
    }
  }

  /**
   * Get invoices with optional filters
   */
  static async getInvoices(filter?: InvoiceFilter): Promise<Invoice[]> {
    try {
      const params = new URLSearchParams();
      if (filter?.status) params.append('status', filter.status);
      if (filter?.vendorName) params.append('vendorName', filter.vendorName);
      if (filter?.dateFrom) params.append('dateFrom', filter.dateFrom);
      if (filter?.dateTo) params.append('dateTo', filter.dateTo);

      const headers = await getAuthHeaders();
      const response = await fetch(`${API_ENDPOINT}/invoices?${params.toString()}`, {
        headers
      });

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
   * Get a single invoice by ID with matched POs and audit trail
   */
  static async getInvoiceById(invoiceId: string): Promise<any> {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_ENDPOINT}/invoices/${invoiceId}`, {
        headers
      });

      if (!response.ok) {
        if (response.status === 404) {
          return null;
        }
        throw new Error('Failed to fetch invoice');
      }

      const data = await response.json();
      return data; // Returns { invoice, matchedPOs, auditTrail }
    } catch (error) {
      console.error('Error fetching invoice:', error);
      throw error;
    }
  }

  /**
   * Approve an invoice
   */
  static async approveInvoice(invoiceId: string, comment: string, userId: string): Promise<void> {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_ENDPOINT}/invoices/${invoiceId}/approve`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ comment })
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
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_ENDPOINT}/invoices/${invoiceId}/reject`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ reason })
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

  /**
   * Parse CSV file to invoice metadata
   */
  static async parseCSVFile(file: File): Promise<InvoiceMetadata> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (e) => {
        try {
          const text = e.target?.result as string;
          const lines = text.split('\n').filter(line => line.trim());

          if (lines.length < 2) {
            throw new Error('CSV file is empty or invalid');
          }

          // Parse header
          const headers = lines[0].split(',').map(h => h.trim());

          // Parse invoice metadata from first data row
          const firstRow = lines[1].split(',').map(v => v.trim());
          const vendorName = firstRow[headers.indexOf('VendorName')] || '';
          const invoiceNumber = firstRow[headers.indexOf('InvoiceNumber')] || '';

          // Parse line items
          const lineItems: LineItem[] = [];
          for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(',').map(v => v.trim());
            if (values.length < headers.length) continue;

            lineItems.push({
              LineNumber: i,
              ItemDescription: values[headers.indexOf('ItemDescription')] || '',
              Quantity: parseFloat(values[headers.indexOf('Quantity')] || '0'),
              UnitPrice: parseFloat(values[headers.indexOf('UnitPrice')] || '0'),
              TotalPrice: parseFloat(values[headers.indexOf('TotalPrice')] || '0')
            });
          }

          const totalAmount = lineItems.reduce((sum, item) => sum + Number(item.TotalPrice), 0);

          resolve({
            vendorName,
            invoiceNumber,
            totalAmount,
            lineItems
          });
        } catch (error) {
          reject(new Error(`Failed to parse CSV: ${(error as Error).message}`));
        }
      };

      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsText(file);
    });
  }

  /**
   * Parse JSON file to invoice metadata
   */
  static async parseJSONFile(file: File): Promise<InvoiceMetadata> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (e) => {
        try {
          const text = e.target?.result as string;
          const data = JSON.parse(text);

          // Validate required fields
          if (!data.vendorName || !data.invoiceNumber || !data.lineItems) {
            throw new Error('Missing required fields in JSON');
          }

          const lineItems: LineItem[] = data.lineItems.map((item: any, index: number) => ({
            LineNumber: index + 1,
            ItemDescription: item.ItemDescription || item.itemDescription || '',
            Quantity: parseFloat(item.Quantity || item.quantity || '0'),
            UnitPrice: parseFloat(item.UnitPrice || item.unitPrice || '0'),
            TotalPrice: parseFloat(item.TotalPrice || item.totalPrice || '0')
          }));

          const totalAmount = lineItems.reduce((sum, item) => sum + Number(item.TotalPrice), 0);

          resolve({
            vendorName: data.vendorName,
            invoiceNumber: data.invoiceNumber,
            totalAmount,
            lineItems
          });
        } catch (error) {
          reject(new Error(`Failed to parse JSON: ${(error as Error).message}`));
        }
      };

      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsText(file);
    });
  }

  /**
   * Parse PDF file to invoice metadata using backend API
   */
  static async parsePDFFile(file: File): Promise<InvoiceMetadata> {
    try {
      // Convert file to base64
      const base64 = await this.fileToBase64(file);

      const headers = await getAuthHeaders();
      const response = await fetch(`${API_ENDPOINT}/invoices/parse-pdf`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          fileName: file.name,
          fileContent: base64
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to parse PDF');
      }

      const data = await response.json();
      return data.metadata;
    } catch (error) {
      console.error('Error parsing PDF:', error);
      throw new Error(`Failed to parse PDF: ${(error as Error).message}`);
    }
  }

  /**
   * Convert file to base64 string
   */
  private static fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = (reader.result as string).split(',')[1];
        resolve(base64);
      };
      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsDataURL(file);
    });
  }

  /**
   * Validate invoice metadata
   */
  private static validateInvoice(metadata: InvoiceMetadata): string[] {
    const errors: string[] = [];

    if (!metadata.vendorName || metadata.vendorName.trim() === '') {
      errors.push('Vendor name is required');
    }

    if (!metadata.invoiceNumber || metadata.invoiceNumber.trim() === '') {
      errors.push('Invoice number is required');
    }

    if (!metadata.lineItems || metadata.lineItems.length === 0) {
      errors.push('At least one line item is required');
    }

    metadata.lineItems.forEach((item, index) => {
      if (!item.ItemDescription || item.ItemDescription.trim() === '') {
        errors.push(`Line item ${index + 1}: Item description is required`);
      }
      if (Number(item.Quantity) <= 0) {
        errors.push(`Line item ${index + 1}: Quantity must be greater than 0`);
      }
      if (Number(item.UnitPrice) <= 0) {
        errors.push(`Line item ${index + 1}: Unit price must be greater than 0`);
      }
    });

    return errors;
  }
}
