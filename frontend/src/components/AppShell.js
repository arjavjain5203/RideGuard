"use client";

import Navbar from "@/components/Navbar";
import { AuthProvider } from "@/context/AuthContext";
import { ToastProvider } from "@/context/ToastContext";

export default function AppShell({ children }) {
  return (
    <AuthProvider>
      <ToastProvider>
        <Navbar />
        <main>{children}</main>
      </ToastProvider>
    </AuthProvider>
  );
}
