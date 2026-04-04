"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { fetchPolicies, fetchScore, fetchEarnings, triggerEvent } from "@/services/api";
import Sidebar from "@/components/Sidebar";
import Card from "@/components/Card";
import Loader from "@/components/Loader";
import { FaShieldAlt, FaStar, FaRupeeSign, FaCloudShowersHeavy, FaCheckCircle, FaExclamationTriangle } from "react-icons/fa";

export default function Dashboard() {
  const { riderId, user, isRider, loading: authLoading } = useAuth();
  const toast = useToast();
  const router = useRouter();
  
  const [data, setData] = useState({
    policy: null,
    score: null,
    earnings: null,
  });
  const [loading, setLoading] = useState(true);
  const [triggerLoading, setTriggerLoading] = useState(false);

  const loadData = useCallback(async () => {
    if (!riderId) return;
    try {
      const [policiesRes, scoreRes, earningsRes] = await Promise.all([
        fetchPolicies(riderId).catch(() => []),
        fetchScore(riderId).catch(() => null),
        fetchEarnings(riderId).catch(() => null),
      ]);
      
      const activePolicy = policiesRes.find(p => p.status === "active");
      
      setData({
        policy: activePolicy || null,
        score: scoreRes,
        earnings: earningsRes,
      });
    } catch (err) {
      console.error(err);
      toast.error("Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  }, [riderId, toast]);

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
    loadData();
  }, [authLoading, isRider, riderId, router, loadData, user]);

  const simulateTrigger = async () => {
    setTriggerLoading(true);
    try {
      // Simulate heavy rain in rider's zone
      const payload = {
        zone: data.earnings?.zone || "Koramangala",
        rainfall_mm_hr: 18.0, // Above 15mm threshold
        temperature_c: 28.0,
        aqi: 80.0,
        traffic_speed_kmh: 15.0,
      };
      
      const response = await triggerEvent(payload);
      
      if (response.claims_created > 0) {
        toast.custom(({ dismiss }) => (
          <div className="bg-white px-6 py-4 shadow-xl rounded-xl border-l-4 border-green-500 flex items-start gap-4 max-w-md">
            <FaCheckCircle className="text-green-500 text-2xl mt-0.5" />
            <div>
              <h3 className="font-bold text-gray-900">
                {response.payouts_created > 0 ? "Claim and Payout Completed!" : "Claim Auto-Generated!"}
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                Heavy rain detected in {payload.zone}. {response.payouts_created > 0
                  ? `${response.payouts_created} payout(s) were completed automatically.`
                  : "A claim was created, but no payout was completed automatically."}
              </p>
              <button 
                onClick={() => { dismiss(); router.push("/payout"); }}
                className="mt-3 text-sm font-semibold text-green-600 hover:text-green-800"
              >
                View Payout &rarr;
              </button>
            </div>
          </div>
        ), { duration: 6000 });
        
        // Reload data to reflect score updates
        loadData();
      } else {
        toast.error("No claims created. Rider may not be eligible or missing required coverage.");
      }
    } catch (err) {
      toast.error("Trigger simulation failed.");
    } finally {
      setTriggerLoading(false);
    }
  };

  if (authLoading || loading) return <Loader fullScreen text="Loading your protection dashboard..." />;

  const { policy, score, earnings } = data;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex gap-8">
        <Sidebar />
        
        <div className="flex-1 space-y-6">
          <div className="flex justify-between items-end mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
              <p className="text-gray-600 mt-1">Welcome back, {earnings?.name || "Partner"}</p>
            </div>
            
            {policy && (
              <button 
                onClick={simulateTrigger}
                disabled={triggerLoading}
                className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white px-4 py-2 rounded-lg font-medium shadow-md transition-all active:scale-95 disabled:opacity-70"
              >
                {triggerLoading ? <Loader /> : <FaCloudShowersHeavy />}
                Simulate Rain Trigger
              </button>
            )}
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {/* Trust Score Card */}
            <Card className="bg-gradient-to-br from-green-50 to-white">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-green-100 rounded-lg"><FaStar className="text-green-600" /></div>
                <h3 className="font-semibold text-gray-700">Unified Trust Score</h3>
              </div>
              <div className="mt-4">
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-extrabold text-gray-900">{score?.urts_score || 70}</span>
                  <span className="text-gray-500 font-medium">/ 100</span>
                </div>
                <div className="mt-3 w-full bg-gray-200 rounded-full h-1.5">
                  <div className="bg-green-500 h-1.5 rounded-full" style={{ width: `${score?.urts_score || 70}%` }}></div>
                </div>
                <p className="text-xs text-gray-500 mt-3 pt-3 border-t border-gray-100 italic">
                  Last updated: {score?.last_event ? score.last_event.replace(/_/g, " ") : "Registration"}
                </p>
                {parseInt(score?.urts_score) < 60 && (
                  <div className="mt-3 bg-red-50 p-2 rounded border border-red-100 flex items-start gap-2">
                    <FaExclamationTriangle className="text-red-500 mt-0.5 shrink-0" />
                    <p className="text-xs text-red-700 font-medium">Warning: Your URTS is below 60. Partial payouts or manual reviews are enforced. Please ensure consistent authentic deliveries to improve your score.</p>
                  </div>
                )}
              </div>
            </Card>

            {/* Policy Status Card */}
            <Card>
              <div className="flex items-center gap-3 mb-2">
                <div className={`p-2 rounded-lg ${policy ? 'bg-blue-100' : 'bg-red-100'}`}>
                  <FaShieldAlt className={policy ? 'text-blue-600' : 'text-red-600'} />
                </div>
                <h3 className="font-semibold text-gray-700">Protection Status</h3>
              </div>
              <div className="mt-4">
                {policy ? (
                  <>
                    <span className="inline-flex px-2 py-1 bg-green-100 text-green-700 text-xs font-bold uppercase rounded tracking-wider mb-2">Active</span>
                    <p className="text-sm font-medium text-gray-900 mb-1">Modules: {Array.isArray(policy.modules) ? policy.modules.join(', ') : 'Various'}</p>
                    <p className="text-xl font-bold text-gray-900 mt-2">₹{policy.weekly_premium} <span className="text-sm font-normal text-gray-500">/ week</span></p>
                  </>
                ) : (
                  <>
                    <span className="inline-flex px-2 py-1 bg-red-100 text-red-700 text-xs font-bold uppercase rounded tracking-wider mb-2">Unprotected</span>
                    <p className="text-sm text-gray-600 mt-1 mb-4">You have no active coverage.</p>
                    <button 
                      onClick={() => router.push("/policy")}
                      className="text-sm font-bold text-white bg-green-600 px-4 py-2 rounded-lg w-full hover:bg-green-700"
                    >
                      Get Protected
                    </button>
                  </>
                )}
              </div>
            </Card>

            {/* Income Card */}
            <Card>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-orange-100 rounded-lg"><FaRupeeSign className="text-orange-600" /></div>
                <h3 className="font-semibold text-gray-700">Protected Income</h3>
              </div>
              <div className="mt-4">
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-extrabold text-gray-900">₹{earnings?.summary?.avg_hourly_income || 0}</span>
                  <span className="text-gray-500">/ hr</span>
                </div>
                <p className="text-sm text-gray-600 mt-2">
                  Basis for parametric payouts.<br/>Calculated from 4-week history.
                </p>
                <div className="mt-4 flex items-center gap-2 text-xs font-medium text-orange-600 bg-orange-50 px-3 py-2 rounded-lg border border-orange-100">
                  <FaExclamationTriangle />
                  Zone: {earnings?.zone || "Unknown"}
                </div>
              </div>
            </Card>
          </div>
          
          {/* Detailed Sections below */}
          <div className="mt-8 bg-white rounded-xl shadow-sm border border-gray-100 p-8 text-center">
            <h3 className="text-lg font-bold text-gray-900 mb-2">All systems operational</h3>
            <p className="text-gray-600 max-w-lg mx-auto">
              Our AI is actively monitoring weather conditions in your zone. You don&apos;t need to do anything. If an eligible event occurs, RideGuard will create the claim and attempt payout automatically.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
