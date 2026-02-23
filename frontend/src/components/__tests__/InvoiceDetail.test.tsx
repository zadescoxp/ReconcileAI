import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import InvoiceDetail from '../InvoiceDetail';
import { InvoiceService } from '../../services/invoiceService';
import { useAuth } from '../../contexts/AuthContext';
import { InvoiceStatus, Severity, DiscrepancyType, FraudFlagType } from '../../types/invoice';

// Mock the services and contexts
jest.mock('../../services/invoiceService');
jest.mock('../../contexts/AuthContext');

const mockInvoiceDetail = {
  invoice: {
    InvoiceId: 'inv-123',
    VendorName: 'Test Vendor',
    InvoiceNumber: 'INV-001',
    InvoiceDate: '2024-01-15',
    LineItems: [
      {
        LineNumber: 1,
        ItemDescription: 'Test Item',
        Quantity: 10,
        UnitPrice: 100,
        TotalPrice: 1000
      }
    ],
    TotalAmount: 1000,
    Status: InvoiceStatus.FLAGGED,
    MatchedPOIds: ['po-123'],
    Discrepancies: [
      {
        type: DiscrepancyType.PRICE_MISMATCH,
        invoiceLine: {
          LineNumber: 1,
          ItemDescription: 'Test Item',
          Quantity: 10,
          UnitPrice: 100,
          TotalPrice: 1000
        },
        poLine: {
          LineNumber: 1,
          ItemDescription: 'Test Item',
          Quantity: 10,
          UnitPrice: 95,
          TotalPrice: 950
        },
        difference: 50,
        description: 'Price is higher than PO'
      }
    ],
    FraudFlags: [
      {
        flagType: FraudFlagType.PRICE_SPIKE,
        severity: Severity.MEDIUM,
        description: 'Price spike detected',
        evidence: { historicalAverage: 90 }
      }
    ],
    AIReasoning: 'Invoice matched with discrepancies',
    ReceivedDate: '2024-01-15',
    S3Key: 's3://bucket/invoice.pdf'
  },
  matchedPOs: [
    {
      POId: 'po-123',
      PONumber: 'PO-001',
      TotalAmount: 950,
      LineItems: [
        {
          LineNumber: 1,
          ItemDescription: 'Test Item',
          Quantity: 10,
          UnitPrice: 95,
          TotalPrice: 950
        }
      ]
    }
  ],
  auditTrail: []
};

const mockUser = {
  userId: 'user-123',
  username: 'testuser',
  email: 'test@example.com',
  role: 'User' as const
};

describe('InvoiceDetail Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useAuth as jest.Mock).mockReturnValue({ user: mockUser });
  });

  describe('Approve Action', () => {
    it('should successfully approve an invoice', async () => {
      (InvoiceService.getInvoiceById as jest.Mock).mockResolvedValue(mockInvoiceDetail);
      (InvoiceService.approveInvoice as jest.Mock).mockResolvedValue(undefined);

      const mockOnBack = jest.fn();
      render(<InvoiceDetail invoiceId="inv-123" onBack={mockOnBack} />);

      // Wait for invoice to load
      await waitFor(() => {
        expect(screen.getByText('Invoice Details')).toBeInTheDocument();
      });

      // Find and click approve button
      const approveButton = screen.getByText('Approve Invoice');
      fireEvent.click(approveButton);

      // Wait for approval to complete
      await waitFor(() => {
        expect(InvoiceService.approveInvoice).toHaveBeenCalledWith(
          'inv-123',
          '',
          'user-123'
        );
      });

      // Check for success message
      await waitFor(() => {
        expect(screen.getByText('Invoice approved successfully')).toBeInTheDocument();
      });
    });

    it('should handle approve action errors', async () => {
      (InvoiceService.getInvoiceById as jest.Mock).mockResolvedValue(mockInvoiceDetail);
      (InvoiceService.approveInvoice as jest.Mock).mockRejectedValue(
        new Error('Network error')
      );

      const mockOnBack = jest.fn();
      render(<InvoiceDetail invoiceId="inv-123" onBack={mockOnBack} />);

      // Wait for invoice to load
      await waitFor(() => {
        expect(screen.getByText('Invoice Details')).toBeInTheDocument();
      });

      // Find and click approve button
      const approveButton = screen.getByText('Approve Invoice');
      fireEvent.click(approveButton);

      // Wait for error message
      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument();
      });
    });
  });

  describe('Reject Action', () => {
    it('should successfully reject an invoice with a reason', async () => {
      (InvoiceService.getInvoiceById as jest.Mock).mockResolvedValue(mockInvoiceDetail);
      (InvoiceService.rejectInvoice as jest.Mock).mockResolvedValue(undefined);

      const mockOnBack = jest.fn();
      render(<InvoiceDetail invoiceId="inv-123" onBack={mockOnBack} />);

      // Wait for invoice to load
      await waitFor(() => {
        expect(screen.getByText('Invoice Details')).toBeInTheDocument();
      });

      // Enter rejection reason
      const commentTextarea = screen.getByPlaceholderText(/Add a comment or reason/i);
      fireEvent.change(commentTextarea, { target: { value: 'Price too high' } });

      // Find and click reject button
      const rejectButton = screen.getByText('Reject Invoice');
      fireEvent.click(rejectButton);

      // Wait for rejection to complete
      await waitFor(() => {
        expect(InvoiceService.rejectInvoice).toHaveBeenCalledWith(
          'inv-123',
          'Price too high',
          'user-123'
        );
      });

      // Check for success message
      await waitFor(() => {
        expect(screen.getByText('Invoice rejected successfully')).toBeInTheDocument();
      });
    });

    it('should require a reason for rejection', async () => {
      (InvoiceService.getInvoiceById as jest.Mock).mockResolvedValue(mockInvoiceDetail);

      const mockOnBack = jest.fn();
      render(<InvoiceDetail invoiceId="inv-123" onBack={mockOnBack} />);

      // Wait for invoice to load
      await waitFor(() => {
        expect(screen.getByText('Invoice Details')).toBeInTheDocument();
      });

      // Try to reject without entering a reason
      const rejectButton = screen.getByText('Reject Invoice');
      
      // Button should be disabled when comment is empty
      expect(rejectButton).toBeDisabled();
    });

    it('should handle reject action errors', async () => {
      (InvoiceService.getInvoiceById as jest.Mock).mockResolvedValue(mockInvoiceDetail);
      (InvoiceService.rejectInvoice as jest.Mock).mockRejectedValue(
        new Error('Server error')
      );

      const mockOnBack = jest.fn();
      render(<InvoiceDetail invoiceId="inv-123" onBack={mockOnBack} />);

      // Wait for invoice to load
      await waitFor(() => {
        expect(screen.getByText('Invoice Details')).toBeInTheDocument();
      });

      // Enter rejection reason
      const commentTextarea = screen.getByPlaceholderText(/Add a comment or reason/i);
      fireEvent.change(commentTextarea, { target: { value: 'Invalid invoice' } });

      // Find and click reject button
      const rejectButton = screen.getByText('Reject Invoice');
      fireEvent.click(rejectButton);

      // Wait for error message
      await waitFor(() => {
        expect(screen.getByText('Server error')).toBeInTheDocument();
      });
    });
  });

  describe('API Error Handling', () => {
    it('should display error when invoice fails to load', async () => {
      (InvoiceService.getInvoiceById as jest.Mock).mockRejectedValue(
        new Error('Failed to fetch invoice')
      );

      const mockOnBack = jest.fn();
      render(<InvoiceDetail invoiceId="inv-123" onBack={mockOnBack} />);

      // Wait for error message
      await waitFor(() => {
        expect(screen.getByText(/Failed to fetch invoice/i)).toBeInTheDocument();
      });
    });

    it('should not show approval actions for non-flagged invoices', async () => {
      const approvedInvoice = {
        ...mockInvoiceDetail,
        invoice: {
          ...mockInvoiceDetail.invoice,
          Status: InvoiceStatus.APPROVED
        }
      };

      (InvoiceService.getInvoiceById as jest.Mock).mockResolvedValue(approvedInvoice);

      const mockOnBack = jest.fn();
      render(<InvoiceDetail invoiceId="inv-123" onBack={mockOnBack} />);

      // Wait for invoice to load
      await waitFor(() => {
        expect(screen.getByText('Invoice Details')).toBeInTheDocument();
      });

      // Approval actions should not be present
      expect(screen.queryByText('Approve Invoice')).not.toBeInTheDocument();
      expect(screen.queryByText('Reject Invoice')).not.toBeInTheDocument();
    });
  });
});
