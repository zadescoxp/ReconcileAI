import React, { useState } from 'react';
import InvoiceList from '../components/InvoiceList';
import InvoiceDetail from '../components/InvoiceDetail';

const InvoicesPage: React.FC = () => {
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);

  const handleInvoiceClick = (invoiceId: string) => {
    setSelectedInvoiceId(invoiceId);
  };

  const handleBackToList = () => {
    setSelectedInvoiceId(null);
  };

  return (
    <div>
      {selectedInvoiceId ? (
        <InvoiceDetail invoiceId={selectedInvoiceId} onBack={handleBackToList} />
      ) : (
        <InvoiceList onInvoiceClick={handleInvoiceClick} />
      )}
    </div>
  );
};

export default InvoicesPage;
