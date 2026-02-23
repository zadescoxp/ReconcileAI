import React, { useState, useRef } from 'react';
import { POService } from '../services/poService';
import { POMetadata, POUploadResult } from '../types/po';
import { useAuth } from '../contexts/AuthContext';
import './POUpload.css';

interface POUploadProps {
  onUploadSuccess?: (poId: string) => void;
}

const POUpload: React.FC<POUploadProps> = ({ onUploadSuccess }) => {
  const { user } = useAuth();
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<POUploadResult | null>(null);
  const [parsedData, setParsedData] = useState<POMetadata | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  };

  const handleFileSelect = async (selectedFile: File) => {
    setResult(null);
    setParsedData(null);

    // Validate file type
    const fileExtension = selectedFile.name.split('.').pop()?.toLowerCase();
    if (fileExtension !== 'csv' && fileExtension !== 'json') {
      setResult({
        success: false,
        message: 'Invalid file type. Please upload a CSV or JSON file.',
        errors: ['Only .csv and .json files are supported']
      });
      return;
    }

    setFile(selectedFile);

    // Parse file
    try {
      let metadata: POMetadata;
      if (fileExtension === 'csv') {
        metadata = await POService.parseCSVFile(selectedFile);
      } else {
        metadata = await POService.parseJSONFile(selectedFile);
      }
      setParsedData(metadata);
    } catch (error) {
      setResult({
        success: false,
        message: (error as Error).message,
        errors: [(error as Error).message]
      });
    }
  };

  const handleUpload = async () => {
    if (!parsedData || !user) {
      return;
    }

    setUploading(true);
    setResult(null);

    try {
      const uploadResult = await POService.uploadPO(parsedData, user.userId);
      setResult(uploadResult);

      if (uploadResult.success && uploadResult.poId) {
        // Clear form on success
        setFile(null);
        setParsedData(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }

        // Notify parent component
        if (onUploadSuccess) {
          onUploadSuccess(uploadResult.poId);
        }
      }
    } catch (error) {
      setResult({
        success: false,
        message: 'Upload failed',
        errors: [(error as Error).message]
      });
    } finally {
      setUploading(false);
    }
  };

  const handleClear = () => {
    setFile(null);
    setParsedData(null);
    setResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="po-upload">
      <h2>Upload Purchase Order</h2>

      <div
        className={`drop-zone ${isDragging ? 'dragging' : ''}`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.json"
          onChange={handleFileInputChange}
          style={{ display: 'none' }}
        />
        <div className="drop-zone-content">
          <svg
            className="upload-icon"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <p className="drop-zone-text">
            {file ? file.name : 'Drag and drop a CSV or JSON file here'}
          </p>
          <p className="drop-zone-subtext">or click to browse</p>
        </div>
      </div>

      {parsedData && (
        <div className="parsed-data">
          <h3>Parsed PO Data</h3>
          <div className="data-summary">
            <div className="data-row">
              <span className="data-label">Vendor:</span>
              <span className="data-value">{parsedData.vendorName}</span>
            </div>
            <div className="data-row">
              <span className="data-label">PO Number:</span>
              <span className="data-value">{parsedData.poNumber}</span>
            </div>
            <div className="data-row">
              <span className="data-label">Total Amount:</span>
              <span className="data-value">${parsedData.totalAmount.toFixed(2)}</span>
            </div>
            <div className="data-row">
              <span className="data-label">Line Items:</span>
              <span className="data-value">{parsedData.lineItems.length}</span>
            </div>
          </div>

          <div className="line-items">
            <h4>Line Items</h4>
            <table>
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
                {parsedData.lineItems.map((item) => (
                  <tr key={item.LineNumber}>
                    <td>{item.LineNumber}</td>
                    <td>{item.ItemDescription}</td>
                    <td>{item.Quantity}</td>
                    <td>${item.UnitPrice.toFixed(2)}</td>
                    <td>${item.TotalPrice.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="upload-actions">
            <button
              className="btn btn-primary"
              onClick={handleUpload}
              disabled={uploading}
            >
              {uploading ? 'Uploading...' : 'Upload PO'}
            </button>
            <button
              className="btn btn-secondary"
              onClick={handleClear}
              disabled={uploading}
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {result && (
        <div className={`upload-result ${result.success ? 'success' : 'error'}`}>
          <p className="result-message">{result.message}</p>
          {result.errors && result.errors.length > 0 && (
            <ul className="error-list">
              {result.errors.map((error, index) => (
                <li key={index}>{error}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};

export default POUpload;
