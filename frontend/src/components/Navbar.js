"use client";

import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { FaShieldAlt, FaUserCircle } from 'react-icons/fa';

export default function Navbar() {
  const { riderId, logout } = useAuth();

  return (
    <nav className="bg-white shadow-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link href="/" className="flex items-center gap-2">
              <FaShieldAlt className="text-green-600 text-2xl" />
              <span className="font-bold text-xl text-gray-900">RideGuard</span>
            </Link>
          </div>
          <div className="flex items-center gap-4">
            {riderId ? (
              <>
                <Link href="/dashboard" className="text-gray-600 hover:text-green-600 font-medium">
                  Dashboard
                </Link>
                <div className="flex items-center gap-2 pl-4 border-l border-gray-200">
                  <FaUserCircle className="text-gray-400 text-xl" />
                  <button onClick={logout} className="text-sm text-red-500 hover:text-red-700 font-medium">
                    Logout
                  </button>
                </div>
              </>
            ) : (
              <Link href="/login" className="text-gray-600 hover:text-green-600 font-medium">
                Login
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
