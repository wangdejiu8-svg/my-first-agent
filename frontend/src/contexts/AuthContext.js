import React, { createContext, useContext, useMemo, useState, useEffect } from 'react';
import { authApi } from '../services/authApi';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);

  useEffect(() => {
    authApi
      .me()
      .then(setUser)
      .catch(() => {
        setUser(null);
      })
      .finally(() => setIsAuthLoading(false));
  }, []);

  const login = async (payload) => {
    const data = await authApi.login(payload);
    setUser(data.user);
    return data.user;
  };

  const register = (payload) => authApi.register(payload);

  const logout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      // Server-side token may already be invalid; local logout should still complete.
    }
    setUser(null);
  };

  const value = useMemo(
    () => ({
      user,
      isLoggedIn: Boolean(user),
      isAuthLoading,
      login,
      logout,
      register,
      setUser,
    }),
    [user, isAuthLoading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider.');
  }
  return context;
}
