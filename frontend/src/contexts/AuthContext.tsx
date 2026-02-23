import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { fetchAuthSession, fetchUserAttributes, signOut as amplifySignOut } from 'aws-amplify/auth';
import { User, Role } from '../types/auth';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loadUser = async () => {
    try {
      const session = await fetchAuthSession();
      if (!session.tokens) {
        setUser(null);
        setLoading(false);
        return;
      }

      const attributes = await fetchUserAttributes();
      
      // Extract user info from Cognito attributes
      const userId = attributes.sub || '';
      const username = attributes.email || '';
      const email = attributes.email || '';
      const roleStr = attributes['custom:role'] || 'User';
      const role = roleStr === 'Admin' ? Role.ADMIN : Role.USER;

      setUser({
        userId,
        username,
        email,
        role
      });
    } catch (error) {
      console.error('Error loading user:', error);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUser();
  }, []);

  const signOut = async () => {
    try {
      await amplifySignOut();
      setUser(null);
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  const refreshUser = async () => {
    setLoading(true);
    await loadUser();
  };

  return (
    <AuthContext.Provider value={{ user, loading, signOut, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};
