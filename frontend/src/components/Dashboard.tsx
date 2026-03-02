import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Role } from '../types/auth';
import Layout from './Layout';
import DashboardHome from '../pages/DashboardHome';
import POsPage from '../pages/POsPage';
import InvoicesPage from '../pages/InvoicesPage';
import AuditTrailPage from '../pages/AuditTrailPage';
import EmailConfigPage from '../pages/EmailConfigPage';
import ProtectedRoute from './ProtectedRoute';

const Dashboard: React.FC = () => {
  const { user } = useAuth();

  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<DashboardHome />} />
          <Route path="pos" element={<POsPage />} />
          <Route path="invoices" element={<InvoicesPage />} />
          <Route
            path="audit"
            element={
              <ProtectedRoute requiredRole={Role.ADMIN}>
                <AuditTrailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="email-config"
            element={
              <ProtectedRoute requiredRole={Role.ADMIN}>
                <EmailConfigPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Router>
  );
};

export default Dashboard;
