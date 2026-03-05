// PO Service for API interactions
import { PO, POMetadata, POSearchQuery, POUploadResult, LineItem } from '../types/po';
import { fetchAuthSession } from 'aws-amplify/auth';

const API_ENDPOINT = process.env.REACT_APP_API_ENDPOINT || 'http://localhost:3001/api';

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

export class POService {
  /**
   * Upload a PO to the backend
   */
  static async uploadPO(metadata: POMetadata, userId: string): Promise<POUploadResult> {
    try {
      // Validate PO data
      const validationErrors = this.validatePO(metadata);
      if (validationErrors.length > 0) {
        return {
          success: false,
          message: 'PO validation failed',
          errors: validationErrors
        };
      }

      const headers = await getAuthHeaders();
      const response = await fetch(`${API_ENDPOINT}/pos`, {
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
          message: error.message || 'Failed to upload PO',
          errors: error.errors
        };
      }

      const result = await response.json();
      return {
        success: true,
        poId: result.poId,
        message: 'PO uploaded successfully'
      };
    } catch (error) {
      console.error('Error uploading PO:', error);
      return {
        success: false,
        message: 'Network error: Unable to connect to server',
        errors: [(error as Error).message]
      };
    }
  }

  /**
   * Search for POs based on query parameters
   */
  static async searchPOs(query: POSearchQuery): Promise<PO[]> {
    try {
      const params = new URLSearchParams();
      if (query.poNumber) params.append('poNumber', query.poNumber);
      if (query.vendorName) params.append('vendorName', query.vendorName);
      if (query.dateFrom) params.append('dateFrom', query.dateFrom);
      if (query.dateTo) params.append('dateTo', query.dateTo);

      const headers = await getAuthHeaders();
      const response = await fetch(`${API_ENDPOINT}/pos?${params.toString()}`, {
        headers
      });

      if (!response.ok) {
        throw new Error('Failed to search POs');
      }

      const data = await response.json();
      return data.pos || [];
    } catch (error) {
      console.error('Error searching POs:', error);
      throw error;
    }
  }

  /**
   * Get a single PO by ID
   */
  static async getPOById(poId: string): Promise<PO | null> {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_ENDPOINT}/pos/${poId}`, {
        headers
      });

      if (!response.ok) {
        if (response.status === 404) {
          return null;
        }
        throw new Error('Failed to fetch PO');
      }

      const data = await response.json();
      return data.po;
    } catch (error) {
      console.error('Error fetching PO:', error);
      throw error;
    }
  }

  /**
   * Parse CSV file to PO metadata
   */
  static async parseCSVFile(file: File): Promise<POMetadata> {
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

          // Parse PO metadata from first data row
          const firstRow = lines[1].split(',').map(v => v.trim());
          const vendorName = firstRow[headers.indexOf('VendorName')] || '';
          const poNumber = firstRow[headers.indexOf('PONumber')] || '';

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
            poNumber,
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
   * Parse JSON file to PO metadata
   */
  static async parseJSONFile(file: File): Promise<POMetadata> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (e) => {
        try {
          const text = e.target?.result as string;
          const data = JSON.parse(text);

          // Validate required fields
          if (!data.vendorName || !data.poNumber || !data.lineItems) {
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
            poNumber: data.poNumber,
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
   * Parse PDF file to PO metadata using backend API
   */
  static async parsePDFFile(file: File): Promise<POMetadata> {
    try {
      // Convert file to base64
      const base64 = await this.fileToBase64(file);

      const headers = await getAuthHeaders();
      const response = await fetch(`${API_ENDPOINT}/pos/parse-pdf`, {
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
   * Validate PO metadata
   */
  private static validatePO(metadata: POMetadata): string[] {
    const errors: string[] = [];

    if (!metadata.vendorName || metadata.vendorName.trim() === '') {
      errors.push('Vendor name is required');
    }

    if (!metadata.poNumber || metadata.poNumber.trim() === '') {
      errors.push('PO number is required');
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
