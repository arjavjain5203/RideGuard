"use client";

import { createContext, useContext, useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { fetchRider } from '@/services/api';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [riderId, setRiderId] = useState(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const checkSession = async () => {
      const storedRiderId = localStorage.getItem('rideguard_rider_id');
      if (storedRiderId) {
        try {
          // Verify session exists in our database
          await fetchRider(storedRiderId);
          setRiderId(storedRiderId);
        } catch (err) {
          // Session is invalid (e.g. database was reset)
          localStorage.removeItem('rideguard_rider_id');
          setRiderId(null);
        }
      }
      setLoading(false);
    };
    checkSession();
  }, []);

  const login = (id) => {
    localStorage.setItem('rideguard_rider_id', id);
    setRiderId(id);
  };

  const logout = () => {
    localStorage.removeItem('rideguard_rider_id');
    setRiderId(null);
    router.push('/');
  };

  return (
    <AuthContext.Provider value={{ riderId, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
