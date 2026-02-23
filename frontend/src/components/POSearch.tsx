import React, { useState, useEffect } from 'react';
import { POService } from '../services/poService';
import { PO, POSearchQuery } from '../types/po';
import './POSearch.css';

interface POSearchProps {
  onPOSelect?: (po: PO) => void;
  refreshTrigger?: number;
}

const POSearch: React.FC<POSearchProps> = ({ onPOSelect, refreshTrigger }) => {
  const [query, setQuery] = useState<POSearchQuery>({});
  const [pos, setPOs] = useState<PO[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedPO, setSelectedPO] = useState<PO | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  useEffect(() => {
    handleSearch();
  }, [refreshTrigger]);

  const handleSearch = async () => {
    setLoading(true);
    setError(null);
    setCurrentPage(1);

    try {
      const results = await POService.searchPOs(query);
      setPOs(results);
    } catch (err) {
      setError('Failed to search POs. Please try again.');
      console.error('Search error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field: keyof POSearchQuery, value: string) => {
    setQuery(prev => ({
      ...prev,
      [field]: value || undefined
    }));
  };

  const handleClear = () => {
    setQuery({});
    setPOs([]);
    setSelectedPO(null);
    setCurrentPage(1);
  };

  const handlePOClick = (po: PO) => {
    setSelectedPO(po);
    if (onPOSelect) {
      onPOSelect(po);
    }
  };

  const handleCloseDetail = () => {
    setSelectedPO(null);
  };

  // Pagination
  const totalPages = Math.ceil(pos.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentPOs = pos.slice(startIndex, endIndex);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  return (
    <div className="po-search">
      <div className="search-form">
        <h3>Search Purchase Orders</h3>
        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="poNumber">PO Number</label>
            <input
              id="poNumber"
              type="text"
              value={query.poNumber || ''}
              onChange={(e) => handleInputChange('poNumber', e.target.value)}
              placeholder="Enter PO number"
            />
          </div>
          <div className="form-group">
            <label htmlFor="vendorName">Vendor Name</label>
            <input
              id="vendorName"
              type="text"
              value={query.vendorName || ''}
              onChange={(e) => handleInputChange('vendorName', e.target.value)}
              placeholder="Enter vendor name"
            />
          </div>
          <div className="form-group">
            <label htmlFor="dateFrom">Date From</label>
            <input
              id="dateFrom"
              type="date"
              value={query.dateFrom || ''}
              onChange={(e) => handleInputChange('dateFrom', e.target.value)}
            />
          </div>
          <div className="form-group">
            <label htmlFor="dateTo">Date To</label>
            <input
              id="dateTo"
              type="date"
              value={query.dateTo || ''}
              onChange={(e) => handleInputChange('dateTo', e.target.value)}
            />
          </div>
        </div>
        <div className="form-actions">
          <button className="btn btn-primary" onClick={handleSearch} disabled={loading}>
            {loading ? 'Searching...' : 'Search'}
          </button>
          <button className="btn btn-secondary" onClick={handleClear}>
            Clear
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {pos.length > 0 && (
        <div className="po-list">
          <h3>Results ({pos.length} POs found)</h3>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>PO Number</th>
                  <th>Vendor</th>
                  <th>Total Amount</th>
                  <th>Upload Date</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {currentPOs.map((po) => (
                  <tr key={po.POId}>
                    <td>{po.PONumber}</td>
                    <td>{po.VendorName}</td>
                    <td>${po.TotalAmount.toFixed(2)}</td>
                    <td>{new Date(po.UploadDate).toLocaleDateString()}</td>
                    <td>
                      <span className={`status-badge status-${po.Status.toLowerCase()}`}>
                        {po.Status}
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn btn-link"
                        onClick={() => handlePOClick(po)}
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                className="btn btn-sm"
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
              >
                Previous
              </button>
              <span className="page-info">
                Page {currentPage} of {totalPages}
              </span>
              <button
                className="btn btn-sm"
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}

      {selectedPO && (
        <div className="modal-overlay" onClick={handleCloseDetail}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>PO Details</h2>
              <button className="close-btn" onClick={handleCloseDetail}>
                &times;
              </button>
            </div>
            <div className="modal-body">
              <div className="detail-section">
                <h3>General Information</h3>
                <div className="detail-grid">
                  <div className="detail-item">
                    <span className="detail-label">PO Number:</span>
                    <span className="detail-value">{selectedPO.PONumber}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Vendor:</span>
                    <span className="detail-value">{selectedPO.VendorName}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Total Amount:</span>
                    <span className="detail-value">${selectedPO.TotalAmount.toFixed(2)}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Upload Date:</span>
                    <span className="detail-value">
                      {new Date(selectedPO.UploadDate).toLocaleString()}
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Status:</span>
                    <span className={`status-badge status-${selectedPO.Status.toLowerCase()}`}>
                      {selectedPO.Status}
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Uploaded By:</span>
                    <span className="detail-value">{selectedPO.UploadedBy}</span>
                  </div>
                </div>
              </div>

              <div className="detail-section">
                <h3>Line Items</h3>
                <table className="detail-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Description</th>
                      <th>Quantity</th>
                      <th>Unit Price</th>
                      <th>Total Price</th>
                      {selectedPO.LineItems.some(item => item.MatchedQuantity !== undefined) && (
                        <th>Matched Qty</th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {selectedPO.LineItems.map((item) => (
                      <tr key={item.LineNumber}>
                        <td>{item.LineNumber}</td>
                        <td>{item.ItemDescription}</td>
                        <td>{item.Quantity}</td>
                        <td>${item.UnitPrice.toFixed(2)}</td>
                        <td>${item.TotalPrice.toFixed(2)}</td>
                        {selectedPO.LineItems.some(i => i.MatchedQuantity !== undefined) && (
                          <td>{item.MatchedQuantity || 0}</td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default POSearch;
