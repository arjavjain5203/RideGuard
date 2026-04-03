"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { fetchPayouts, getClaimDetails, explainClaim } from "@/services/api";
import Sidebar from "@/components/Sidebar";
import Card from "@/components/Card";
import Loader from "@/components/Loader";
import { FaCheckCircle, FaUniversity, FaRobot } from "react-icons/fa";

export default function PayoutPage() {
  const { riderId } = useAuth();
  const router = useRouter();
  
  const [payouts, setPayouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [aiExplanation, setAiExplanation] = useState(null);

  useEffect(() => {
    if (!riderId) {
      router.push("/");
      return;
    }

    const loadData = async () => {
      try {
        const data = await fetchPayouts(riderId);
        // Sort to show latest payout first
        data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        setPayouts(data);
        
        if (data.length > 0) {
          const latest = data[0];
          // Fetch AI Explanation
          const claimInfo = await getClaimDetails(latest.claim_id);
          const aiData = await explainClaim({
            trigger: claimInfo.trigger_type,
            hours: claimInfo.disruption_hours,
            payout: latest.amount,
            urts: claimInfo.effective_urts
          });
          setAiExplanation(aiData.explanation);
        }
      } catch (err) {
        console.error("Failed to load payouts", err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [riderId, router]);

  if (loading) return <Loader fullScreen text="Loading payouts..." />;

  const latestPayout = payouts.length > 0 ? payouts[0] : null;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex gap-8">
        <Sidebar />
        
        <div className="flex-1 space-y-6">
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-gray-900">Payouts</h1>
            <p className="text-gray-600 mt-1">Instant settlements direct to your UPI account.</p>
          </div>

          {!latestPayout ? (
            <Card className="text-center py-16">
              <FaUniversity className="text-gray-300 text-6xl mx-auto mb-4" />
              <h3 className="text-xl font-medium text-gray-900">No payouts yet</h3>
              <p className="text-gray-500 mt-2">When a weather disruption triggers your policy, payout details will appear here.</p>
            </Card>
          ) : (
            <>
              {latestPayout.status === "completed" && (
                <div className="bg-gradient-to-r from-green-500 to-emerald-600 rounded-2xl p-8 text-white shadow-lg text-center mx-auto max-w-2xl mb-8">
                  <div className="bg-white/20 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <FaCheckCircle className="text-4xl text-white" />
                  </div>
                  <h2 className="text-3xl font-extrabold mb-1">₹{latestPayout.amount}</h2>
                  <p className="text-green-50 font-medium text-lg mb-6">Paid Successfully to your UPI</p>
                  
                  <div className="bg-white/10 rounded-xl p-4 text-left backdrop-blur-sm">
                    <div className="flex justify-between border-b border-white/20 pb-2 mb-2">
                      <span className="text-green-100 text-sm">Transaction ID</span>
                      <span className="font-mono text-sm">{latestPayout.upi_transaction_id}</span>
                    </div>
                    <div className="flex justify-between border-b border-white/20 pb-2 mb-2">
                      <span className="text-green-100 text-sm">Date & Time</span>
                      <span className="text-sm">{new Date(latestPayout.paid_at || latestPayout.created_at).toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between border-b border-white/20 pb-2 mb-2">
                      <span className="text-green-100 text-sm">URTS Payout Factor</span>
                      <span className="text-sm font-bold">{latestPayout.urts_factor * 100}%</span>
                    </div>
                    <div className="flex justify-between pt-1">
                      <span className="text-green-100 text-sm">Status</span>
                      <span className="text-sm font-bold uppercase tracking-wider">Settled</span>
                    </div>
                  </div>
                  
                  {aiExplanation && (
                    <div className="mt-6 bg-white/10 rounded-xl p-4 text-left border border-white/20">
                      <div className="flex items-center gap-2 mb-2 text-green-50">
                        <FaRobot className="text-lg" />
                        <span className="font-bold text-sm">AI Explanation</span>
                      </div>
                      <p className="text-sm text-green-50 leading-relaxed italic">
                        "{aiExplanation}"
                      </p>
                    </div>
                  )}
                </div>
              )}

              <h3 className="text-xl font-bold text-gray-900 mb-4">Transfer History</h3>
              <div className="space-y-4">
                {payouts.map((payout) => (
                  <Card key={payout.id} noPadding>
                    <div className="p-4 flex justify-between items-center">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                          <FaUniversity className="text-blue-600" />
                        </div>
                        <div>
                          <p className="font-bold text-gray-900">UPI Transfer</p>
                          <p className="font-mono text-xs text-gray-500">{payout.upi_transaction_id}</p>
                          <p className="text-xs text-gray-500 mt-0.5">{new Date(payout.created_at).toLocaleString()}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xl font-extrabold text-gray-900">+₹{payout.amount}</div>
                        <span className="text-xs font-bold text-green-600 bg-green-50 px-2 py-0.5 rounded uppercase">
                          {payout.status}
                        </span>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
