import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

// Configuration flag - set to false to disable auth during development
export const AUTH_ENABLED = false;

interface User {
  id: string;
  username: string;
  role: 'admin' | 'operator' | 'viewer';
  email?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  authEnabled: boolean;
  login: (username: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Mock users for development (replace with real API later)
const MOCK_USERS: Record<string, { password: string; user: User }> = {
  admin: {
    password: 'hydra',
    user: {
      id: 'admin-001',
      username: 'admin',
      role: 'admin',
      email: 'admin@hydra.local',
    },
  },
  operator: {
    password: 'operator123',
    user: {
      id: 'op-001',
      username: 'operator',
      role: 'operator',
    },
  },
  viewer: {
    password: 'viewer123',
    user: {
      id: 'viewer-001',
      username: 'viewer',
      role: 'viewer',
    },
  },
};

const AUTH_TOKEN_KEY = 'hydra_auth_token';
const AUTH_USER_KEY = 'hydra_auth_user';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = useCallback(async () => {
    setIsLoading(true);

    // If auth is disabled, auto-authenticate as admin
    if (!AUTH_ENABLED) {
      setUser(MOCK_USERS.admin.user);
      setIsLoading(false);
      return;
    }

    try {
      // Check localStorage for existing session
      const storedUser = localStorage.getItem(AUTH_USER_KEY);
      const token = localStorage.getItem(AUTH_TOKEN_KEY);

      if (storedUser && token) {
        // In production, verify token with API here
        const parsedUser = JSON.parse(storedUser);
        setUser(parsedUser);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      localStorage.removeItem(AUTH_TOKEN_KEY);
      localStorage.removeItem(AUTH_USER_KEY);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = useCallback(async (username: string, password: string): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);

    try {
      // Simulate network delay
      await new Promise(resolve => setTimeout(resolve, 500));

      // Check mock users (replace with real API call)
      const mockUser = MOCK_USERS[username.toLowerCase()];

      if (!mockUser || mockUser.password !== password) {
        return { success: false, error: 'Invalid username or password' };
      }

      // Generate mock token (replace with real JWT from API)
      const token = btoa(`${username}:${Date.now()}`);

      // Store session
      localStorage.setItem(AUTH_TOKEN_KEY, token);
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(mockUser.user));

      setUser(mockUser.user);
      return { success: true };

    } catch (error) {
      console.error('Login failed:', error);
      return { success: false, error: 'Login failed. Please try again.' };
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    setUser(null);
  }, []);

  const isAuthenticated = AUTH_ENABLED ? !!user : true;

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        isLoading,
        authEnabled: AUTH_ENABLED,
        login,
        logout,
        checkAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Higher-order component for protected routes
export const withAuth = <P extends object>(
  WrappedComponent: React.ComponentType<P>,
  requiredRole?: User['role']
) => {
  return function WithAuthComponent(props: P) {
    const { isAuthenticated, user, authEnabled, isLoading } = useAuth();

    if (isLoading) {
      return (
        <div className="h-screen w-screen flex items-center justify-center bg-surface-base">
          <div className="animate-pulse text-emerald-500 font-mono">AUTHENTICATING...</div>
        </div>
      );
    }

    if (authEnabled && !isAuthenticated) {
      return null; // Will be handled by the login page redirect
    }

    if (requiredRole && user?.role !== requiredRole && user?.role !== 'admin') {
      return (
        <div className="h-screen w-screen flex items-center justify-center bg-surface-base">
          <div className="text-red-500 font-mono">ACCESS DENIED: Insufficient permissions</div>
        </div>
      );
    }

    return <WrappedComponent {...props} />;
  };
};
