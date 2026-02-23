import React, { useState } from 'react';
import POUpload from '../components/POUpload';
import POSearch from '../components/POSearch';
import './POsPage.css';

const POsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'upload' | 'search'>('upload');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleUploadSuccess = (poId: string) => {
    console.log('PO uploaded successfully:', poId);
    // Trigger refresh of search results
    setRefreshTrigger(prev => prev + 1);
    // Switch to search tab to see the uploaded PO
    setActiveTab('search');
  };

  return (
    <div className="pos-page">
      <div className="page-header">
        <h1>Purchase Orders</h1>
        <p>Upload and manage purchase orders for invoice matching</p>
      </div>

      <div className="tabs">
        <button
          className={`tab ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          Upload PO
        </button>
        <button
          className={`tab ${activeTab === 'search' ? 'active' : ''}`}
          onClick={() => setActiveTab('search')}
        >
          Search POs
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'upload' && (
          <POUpload onUploadSuccess={handleUploadSuccess} />
        )}
        {activeTab === 'search' && (
          <POSearch refreshTrigger={refreshTrigger} />
        )}
      </div>
    </div>
  );
};

export default POsPage;
