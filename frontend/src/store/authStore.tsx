import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { User } from '@/types';
import * as authApi from '@/api/auth';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const stored = localStorage.getItem('eduscale_user');
    return stored ? JSON.parse(stored) : null;
  });
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem('eduscale_token'),
  );
  const [isLoading, setIsLoading] = useState(true);

  // Verify token on mount
  useEffect(() => {
    if (token) {
      authApi.getMe()
        .then((u) => {
          setUser(u);
          localStorage.setItem('eduscale_user', JSON.stringify(u));
        })
        .catch(() => {
          setUser(null);
          setToken(null);
          localStorage.removeItem('eduscale_token');
          localStorage.removeItem('eduscale_user');
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login(email, password);
    setToken(res.access_token);
    setUser(res.user);
    localStorage.setItem('eduscale_token', res.access_token);
    localStorage.setItem('eduscale_user', JSON.stringify(res.user));
  }, []);

  const logout = useCallback(() => {
    authApi.logout().catch(() => {});
    setToken(null);
    setUser(null);
    localStorage.removeItem('eduscale_token');
    localStorage.removeItem('eduscale_user');
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

