import { createContext, useContext, ReactNode } from 'react';
import { User, Role } from '../types/auth';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

// Mock user for development
const mockUser: User = {
  userId: 'dev-user-123',
  username: 'developer@example.com',
  email: 'developer@example.com',
  role: Role.ADMIN
};

const MockAuthContext = createContext<AuthContextType>({
  user: mockUser,
  loading: false,
  signIn: async () => {},
  signOut: async () => {}
});

export const MockAuthProvider = ({ children }: { children: ReactNode }) => {
  const value: AuthContextType = {
    user: mockUser,
    loading: false,
    signIn: async (username: string, password: string) => {
      console.log('Mock sign in:', username);
    },
    signOut: async () => {
      console.log('Mock sign out');
    }
  };

  return (
    <MockAuthContext.Provider value={value}>
      {children}
    </MockAuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(MockAuthContext);
  if (!context) {
    throw new Error('useAuth must be used within MockAuthProvider');
  }
  return context;
};
