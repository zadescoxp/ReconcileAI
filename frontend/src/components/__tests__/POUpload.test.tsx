/**
 * Unit Tests for PO Upload Component
 * Tests file upload with valid PO, invalid PO, and API error handling
 * Validates: Requirements 2.1, 2.2
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import POUpload from '../POUpload';
import { POService } from '../../services/poService';
import { useAuth } from '../../contexts/AuthContext';
import { Role } from '../../types/auth';

// Mock the POService
jest.mock('../../services/poService');

// Mock the useAuth hook
jest.mock('../../contexts/AuthContext');

// Mock user for AuthContext
const mockUser = {
  userId: 'test-user-123',
  username: 'testuser',
  email: 'test@example.com',
  role: Role.USER
};

describe('POUpload Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useAuth as jest.Mock).mockReturnValue({
      user: mockUser,
      signOut: jest.fn(),
      refreshUser: jest.fn()
    });
  });

  test('renders upload component with drop zone', () => {
    render(<POUpload />);
    
    expect(screen.getByText(/Upload Purchase Order/i)).toBeInTheDocument();
    expect(screen.getByText(/Drag and drop a CSV or JSON file here/i)).toBeInTheDocument();
  });

  test('handles valid CSV file upload successfully', async () => {
    const mockPOMetadata = {
      vendorName: 'Test Vendor',
      poNumber: 'PO-12345',
      totalAmount: 1000,
      lineItems: [
        {
          LineNumber: 1,
          ItemDescription: 'Test Item',
          Quantity: 10,
          UnitPrice: 100,
          TotalPrice: 1000
        }
      ]
    };

    const mockUploadResult = {
      success: true,
      poId: 'po-123',
      message: 'PO uploaded successfully'
    };

    (POService.parseCSVFile as jest.Mock).mockResolvedValue(mockPOMetadata);
    (POService.uploadPO as jest.Mock).mockResolvedValue(mockUploadResult);

    render(<POUpload />);

    const csvContent = 'VendorName,PONumber,ItemDescription,Quantity,UnitPrice,TotalPrice\nTest Vendor,PO-12345,Test Item,10,100,1000';
    const file = new File([csvContent], 'test.csv', { type: 'text/csv' });

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false
    });
    
    fireEvent.change(input);

    await waitFor(() => {
      expect(screen.getByText(/Parsed PO Data/i)).toBeInTheDocument();
    });

    expect(screen.getByText('Test Vendor')).toBeInTheDocument();
    expect(screen.getByText('PO-12345')).toBeInTheDocument();

    const uploadButton = screen.getByRole('button', { name: /Upload PO/i });
    fireEvent.click(uploadButton);

    await waitFor(() => {
      expect(screen.getByText(/PO uploaded successfully/i)).toBeInTheDocument();
    });

    expect(POService.uploadPO).toHaveBeenCalledWith(mockPOMetadata, mockUser.userId);
  });

  test('rejects invalid file type', async () => {
    render(<POUpload />);

    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false
    });
    
    fireEvent.change(input);

    await waitFor(() => {
      expect(screen.getByText(/Invalid file type/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Only .csv and .json files are supported/i)).toBeInTheDocument();
  });

  test('handles invalid PO data with validation errors', async () => {
    const mockUploadResult = {
      success: false,
      message: 'PO validation failed',
      errors: ['Vendor name is required', 'PO number is required']
    };

    const mockPOMetadata = {
      vendorName: '',
      poNumber: '',
      totalAmount: 0,
      lineItems: []
    };

    (POService.parseCSVFile as jest.Mock).mockResolvedValue(mockPOMetadata);
    (POService.uploadPO as jest.Mock).mockResolvedValue(mockUploadResult);

    render(<POUpload />);

    const csvContent = 'VendorName,PONumber,ItemDescription,Quantity,UnitPrice,TotalPrice\n,,,,0,0';
    const file = new File([csvContent], 'invalid.csv', { type: 'text/csv' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false
    });
    
    fireEvent.change(input);

    await waitFor(() => {
      expect(screen.getByText(/Parsed PO Data/i)).toBeInTheDocument();
    });

    const uploadButton = screen.getByRole('button', { name: /Upload PO/i });
    fireEvent.click(uploadButton);

    await waitFor(() => {
      expect(screen.getByText(/PO validation failed/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Vendor name is required/i)).toBeInTheDocument();
    expect(screen.getByText(/PO number is required/i)).toBeInTheDocument();
  });

  test('handles API error during upload', async () => {
    const mockPOMetadata = {
      vendorName: 'Test Vendor',
      poNumber: 'PO-12345',
      totalAmount: 1000,
      lineItems: [
        {
          LineNumber: 1,
          ItemDescription: 'Test Item',
          Quantity: 10,
          UnitPrice: 100,
          TotalPrice: 1000
        }
      ]
    };

    (POService.parseCSVFile as jest.Mock).mockResolvedValue(mockPOMetadata);
    (POService.uploadPO as jest.Mock).mockResolvedValue({
      success: false,
      message: 'Network error: Unable to connect to server',
      errors: ['Connection timeout']
    });

    render(<POUpload />);

    const csvContent = 'VendorName,PONumber,ItemDescription,Quantity,UnitPrice,TotalPrice\nTest Vendor,PO-12345,Test Item,10,100,1000';
    const file = new File([csvContent], 'test.csv', { type: 'text/csv' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: false
    });
    
    fireEvent.change(input);

    await waitFor(() => {
      expect(screen.getByText(/Parsed PO Data/i)).toBeInTheDocument();
    });

    const uploadButton = screen.getByRole('button', { name: /Upload PO/i });
    fireEvent.click(uploadButton);

    await waitFor(() => {
      expect(screen.getByText(/Network error: Unable to connect to server/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Connection timeout/i)).toBeInTheDocument();
  });
});
