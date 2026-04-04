"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import {
  clearAccessToken,
  fetchCurrentUser,
  getAccessToken,
  setAccessToken,
} from '@/services/api';

const AuthContext = createContext(null);

const ADMIN_PATH_PREFIX = '/admin';

function getDefaultRedirectPath(role) {
  return role === 'admin' ? '/admin' : '/dashboard';
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    let mounted = true;

    const checkSession = async () => {
      const token = getAccessToken();
      if (!token) {
        if (mounted) {
          setUser(null);
          setLoading(false);
        }
        return;
      }

      try {
        const profile = await fetchCurrentUser();
        if (mounted) {
          setUser(profile);
        }
      } catch (err) {
        clearAccessToken();
        if (mounted) {
          setUser(null);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    checkSession();

    const handleUnauthorized = () => {
      clearAccessToken();
      setUser(null);
      router.push(pathname?.startsWith(ADMIN_PATH_PREFIX) ? '/admin/login' : '/login');
    };

    window.addEventListener('rideguard:unauthorized', handleUnauthorized);
    return () => {
      mounted = false;
      window.removeEventListener('rideguard:unauthorized', handleUnauthorized);
    };
  }, [pathname, router]);

  const login = useCallback((authResponse) => {
    setAccessToken(authResponse.access_token);
    setUser(authResponse.user);
  }, []);

  const logout = useCallback(({ redirectTo } = {}) => {
    const currentRole = user?.role;
    clearAccessToken();
    setUser(null);
    router.push(redirectTo || (currentRole === 'admin' ? '/admin/login' : '/login'));
  }, [router, user?.role]);

  const value = useMemo(
    () => ({
      user,
      riderId: user?.role === 'rider' ? user.id : null,
      accountId: user?.id || null,
      role: user?.role || null,
      isAdmin: user?.role === 'admin',
      isRider: user?.role === 'rider',
      isAuthenticated: Boolean(user),
      loading,
      login,
      logout,
      getDefaultRedirectPath,
    }),
    [loading, login, logout, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
