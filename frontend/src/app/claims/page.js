"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { fetchClaims } from "@/services/api";
import Sidebar from "@/components/Sidebar";
import Card from "@/components/Card";
import Loader from "@/components/Loader";
import { FaFileInvoice, FaCheckCircle, FaExclamationCircle } from "react-icons/fa";

export default function Claims() {
  const { riderId, user, isRider, loading: authLoading } = useAuth();
  const router = useRouter();
  
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push("/login");
      return;
    }
    if (!isRider || !riderId) {
      router.push("/admin");
      return;
    }

    const loadData = async () => {
      try {
        const claimsData = await fetchClaims(riderId);
        setClaims(claimsData);
      } catch (err) {
        console.error("Failed to load claims", err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [authLoading, isRider, riderId, router, user]);

  if (authLoading || loading) return <Loader fullScreen text="Loading your claims history..." />;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex gap-8">
        <Sidebar />
        
        <div className="flex-1 space-y-6">
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-gray-900">My Claims</h1>
            <p className="text-gray-600 mt-1">History of all auto-generated parametric claims.</p>
          </div>

          {claims.length === 0 ? (
            <Card className="text-center py-16">
              <FaFileInvoice className="text-gray-300 text-6xl mx-auto mb-4" />
              <h3 className="text-xl font-medium text-gray-900">No claims yet</h3>
              <p className="text-gray-500 mt-2">You haven&apos;t had any weather disruptions during your active policies.</p>
            </Card>
          ) : (
            <div className="space-y-4">
              {claims.map((claim) => {
                return (
                  <Card key={claim.id} noPadding>
                    <div className="p-6 flex flex-col md:flex-row justify-between items-center gap-4">
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                          claim.status === 'paid' ? 'bg-green-100' : claim.status === 'rejected' ? 'bg-red-100' : 'bg-yellow-100'
                        }`}>
                          {claim.status === 'paid' 
                            ? <FaCheckCircle className="text-green-600 text-xl" />
                            : <FaExclamationCircle className={`${claim.status === 'rejected' ? 'text-red-600' : 'text-yellow-600'} text-xl`} />
                          }
                        </div>
                        <div>
                          <h4 className="font-bold text-gray-900 text-lg">
                            {claim.trigger_type.charAt(0).toUpperCase() + claim.trigger_type.slice(1)} Trigger
                          </h4>
                          <p className="text-sm text-gray-500">
                            {new Date(claim.created_at).toLocaleDateString()} at {new Date(claim.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                          </p>
                          <div className="mt-1 flex gap-2">
                            <span className="text-xs font-medium bg-gray-100 text-gray-600 px-2 py-1 rounded">
                              Value: {claim.trigger_value}
                            </span>
                            <span className="text-xs font-medium bg-gray-100 text-gray-600 px-2 py-1 rounded">
                              Disruption: {claim.disruption_hours} hrs
                            </span>
                            <span className="text-xs font-medium bg-gray-100 text-gray-600 px-2 py-1 rounded">
                              URTS: {claim.effective_urts}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="text-2xl font-extrabold text-gray-900">
                          {claim.payout_amount != null ? `₹${claim.payout_amount}` : `₹${claim.loss_amount || 0}`}
                        </div>
                        <span className={`inline-flex mt-1 px-2 py-0.5 rounded text-xs font-bold uppercase ${
                          claim.status === 'paid' 
                            ? 'bg-green-100 text-green-700' 
                            : claim.status === 'rejected'
                              ? 'bg-red-100 text-red-700'
                              : 'bg-yellow-100 text-yellow-700'
                        }`}>
                          {claim.payout_status || claim.status}
                        </span>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
