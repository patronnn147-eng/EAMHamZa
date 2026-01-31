import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useMemo,
  ReactNode,
} from 'react';
import { client } from '@/lib/api';

interface User {
  id: string;
  email: string;
  nom?: string;
  role: string;
  last_login?: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  refetch: () => Promise<void>;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

 export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkAuthStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const me = await client.auth.me();
      setUser(me.data ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async () => {
    try {
      setError(null);
      await checkAuthStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    }
  };

  const logout = async () => {
    try {
      setError(null);
      await client.auth.logout();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Logout failed');
    }
  };

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const value: AuthContextType = useMemo(() => {
    const role = (user?.role ?? '').toUpperCase();
    return {
      user,
      loading,
      error,
      login,
      logout,
      refetch: checkAuthStatus,
      isAdmin: role === 'ADMIN',
    };
  }, [user, loading, error]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
