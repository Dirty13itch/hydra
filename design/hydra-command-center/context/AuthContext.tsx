import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

// Toggle this to enable/disable authentication UI elements
export const AUTH_ENABLED = false;

export interface User {
  id: string;
  username: string;
  role: 'admin' | 'operator' | 'viewer';
  email?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  authEnabled: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Default user for when auth is disabled
const DEFAULT_USER: User = {
  id: 'default-admin',
  username: 'Shaun',
  role: 'admin',
  email: 'admin@hydra.local'
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(AUTH_ENABLED ? null : DEFAULT_USER);
  const [loading, setLoading] = useState(false);

  const login = useCallback(async (username: string, password: string): Promise<boolean> => {
    if (!AUTH_ENABLED) {
      setUser(DEFAULT_USER);
      return true;
    }

    setLoading(true);
    try {
      // TODO: Implement real authentication against Hydra Tools API
      // const response = await fetch('http://192.168.1.244:8700/api/v1/auth/login', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ username, password })
      // });

      // For now, simulate successful login
      await new Promise(resolve => setTimeout(resolve, 500));

      setUser({
        id: 'user-1',
        username,
        role: 'admin'
      });

      return true;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    if (!AUTH_ENABLED) {
      // Don't actually log out when auth is disabled
      return;
    }
    setUser(null);
    // TODO: Clear any stored tokens/sessions
  }, []);

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    authEnabled: AUTH_ENABLED,
    login,
    logout,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
