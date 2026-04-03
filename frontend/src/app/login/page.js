"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import toast from "react-hot-toast";

export default function Login() {
  const [riderId, setInputId] = useState("");
  const router = useRouter();
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (riderId.length > 10) {
      try {
        const { fetchRider } = require("@/services/api");
        await fetchRider(riderId);
        login(riderId);
        toast.success("Welcome back!");
        router.push("/dashboard");
      } catch (err) {
        toast.error("Invalid Rider ID. User not found.");
      }
    } else {
      toast.error("Please enter a valid Rider ID (UUID format).");
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-gray-100 p-8 text-center">
        <h2 className="text-3xl font-extrabold text-gray-900 mb-6">Partner Login</h2>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <input
              type="text"
              required
              className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500 bg-gray-50 border p-4 text-center"
              placeholder="Enter your Rider ID (UUID)"
              value={riderId}
              onChange={(e) => setInputId(e.target.value)}
            />
            <p className="mt-2 text-xs text-gray-500">For demo purposes, you can find this ID from your registration response.</p>
          </div>
          <button
            type="submit"
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 transition-colors"
          >
            Access Dashboard
          </button>
        </form>
      </div>
    </div>
  );
}
