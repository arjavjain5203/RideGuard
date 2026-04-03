"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { fetchPayouts, getClaimDetails } from "@/services/api";
import Sidebar from "@/components/Sidebar";
import Card from "@/components/Card";
import Loader from "@/components/Loader";
import { FaFileInvoice, FaCheckCircle, FaExclamationCircle } from "react-icons/fa";

export default function Claims() {
  const { riderId } = useAuth();
  const router = useRouter();
  
  const [payouts, setPayouts] = useState([]);
  const [claimsDetails, setClaimsDetails] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!riderId) {
      router.push("/");
      return;
    }

    const loadData = async () => {
      try {
        const payoutsData = await fetchPayouts(riderId);
        setPayouts(payoutsData);
        
        // Fetch details for each claim to get trigger type and disruption info
        const details = {};
        for (const p of payoutsData) {
          try {
            const claimInfo = await getClaimDetails(p.claim_id);
            details[p.claim_id] = claimInfo;
          } catch (e) {
            console.error(e);
          }
        }
        setClaimsDetails(details);
      } catch (err) {
        console.error("Failed to load claims", err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [riderId, router]);

  if (loading) return <Loader fullScreen text="Loading your claims history..." />;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex gap-8">
        <Sidebar />
        
        <div className="flex-1 space-y-6">
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-gray-900">My Claims</h1>
            <p className="text-gray-600 mt-1">History of all auto-generated parametric claims.</p>
          </div>

          {payouts.length === 0 ? (
            <Card className="text-center py-16">
              <FaFileInvoice className="text-gray-300 text-6xl mx-auto mb-4" />
              <h3 className="text-xl font-medium text-gray-900">No claims yet</h3>
              <p className="text-gray-500 mt-2">You haven't had any weather disruptions during your active policies.</p>
            </Card>
          ) : (
            <div className="space-y-4">
              {payouts.map((payout) => {
                const claim = claimsDetails[payout.claim_id];
                return (
                  <Card key={payout.id} noPadding>
                    <div className="p-6 flex flex-col md:flex-row justify-between items-center gap-4">
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                          payout.status === 'completed' ? 'bg-green-100' : 'bg-yellow-100'
                        }`}>
                          {payout.status === 'completed' 
                            ? <FaCheckCircle className="text-green-600 text-xl" />
                            : <FaExclamationCircle className="text-yellow-600 text-xl" />
                          }
                        </div>
                        <div>
                          <h4 className="font-bold text-gray-900 text-lg">
                            {claim ? claim.trigger_type.charAt(0).toUpperCase() + claim.trigger_type.slice(1) : 'Weather'} Trigger
                          </h4>
                          <p className="text-sm text-gray-500">
                            {new Date(payout.created_at).toLocaleDateString()} at {new Date(payout.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                          </p>
                          {claim && (
                            <div className="mt-1 flex gap-2">
                              <span className="text-xs font-medium bg-gray-100 text-gray-600 px-2 py-1 rounded">
                                Value: {claim.trigger_value}
                              </span>
                              <span className="text-xs font-medium bg-gray-100 text-gray-600 px-2 py-1 rounded">
                                Disruption: {claim.disruption_hours} hrs
                              </span>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="text-2xl font-extrabold text-gray-900">
                          ₹{payout.amount}
                        </div>
                        <span className={`inline-flex mt-1 px-2 py-0.5 rounded text-xs font-bold uppercase ${
                          payout.status === 'completed' 
                            ? 'bg-green-100 text-green-700' 
                            : 'bg-yellow-100 text-yellow-700'
                        }`}>
                          {payout.status}
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
