import React, { useState } from 'react';
import InvoiceList from '../components/InvoiceList';
import InvoiceDetail from '../components/InvoiceDetail';
import InvoiceUpload from '../components/InvoiceUpload';

const InvoicesPage: React.FC = () => {
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleInvoiceClick = (invoiceId: string) => {
    setSelectedInvoiceId(invoiceId);
  };

  const handleBackToList = () => {
    setSelectedInvoiceId(null);
  };

  const handleUploadSuccess = (invoiceId: string) => {
    setShowUpload(false);
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div>
      {selectedInvoiceId ? (
        <InvoiceDetail invoiceId={selectedInvoiceId} onBack={handleBackToList} />
      ) : (
        <>
          <div style={{ marginBottom: '20px' }}>
            <button
              className="btn btn-primary"
              onClick={() => setShowUpload(!showUpload)}
              style={{ marginBottom: '10px' }}
            >
              {showUpload ? 'Hide Upload' : 'Upload Invoice'}
            </button>
          </div>
          {showUpload && <InvoiceUpload onUploadSuccess={handleUploadSuccess} />}
          <InvoiceList key={refreshKey} onInvoiceClick={handleInvoiceClick} />
        </>
      )}
    </div>
  );
};

export default InvoicesPage;
