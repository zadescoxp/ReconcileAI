import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Role } from '../types/auth';

interface ProtectedRouteProps {
  children: React.ReactElement;
  requiredRole?: Role;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requiredRole }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        Loading...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Check role-based access
  if (requiredRole && user.role !== requiredRole) {
    // If Admin role required but user is not Admin, redirect to dashboard
    if (requiredRole === Role.ADMIN && user.role !== Role.ADMIN) {
      return <Navigate to="/" replace />;
    }
  }

  return children;
};

export default ProtectedRoute;
