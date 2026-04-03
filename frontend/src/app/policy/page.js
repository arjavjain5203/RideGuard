"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { listCoverageModules, calculatePremium, createPolicy, fetchPolicies } from "@/services/api";
import Loader from "@/components/Loader";
import Card from "@/components/Card";
import toast from "react-hot-toast";

export default function PolicySelection() {
  const { riderId } = useAuth();
  const router = useRouter();
  
  const [modules, setModules] = useState([]);
  const [selectedModules, setSelectedModules] = useState([]);
  const [premiumData, setPremiumData] = useState(null);
  
  const [loadingModules, setLoadingModules] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [creating, setCreating] = useState(false);

  // Check if policy already exists
  useEffect(() => {
    if (!riderId) {
      router.push("/");
      return;
    }

    const checkExisting = async () => {
      try {
        const existing = await fetchPolicies(riderId);
        const active = existing.find(p => p.status === "active");
        if (active) {
          toast.success("You already have an active policy. Redirecting to dashboard.");
          router.push("/dashboard");
        } else {
          loadModules();
        }
      } catch (err) {
        loadModules();
      }
    };

    const loadModules = async () => {
      try {
        const data = await listCoverageModules();
        setModules(data);
        // Pre-select first two default
        setSelectedModules([data[0]?.name, data[1]?.name].filter(Boolean));
      } catch (err) {
        toast.error("Failed to load coverage modules");
      } finally {
        setLoadingModules(false);
      }
    };

    checkExisting();
  }, [riderId, router]);

  // Recalculate premium when selection changes
  useEffect(() => {
    if (selectedModules.length === 0) {
      setPremiumData(null);
      return;
    }
    
    const fetchPremium = async () => {
      setCalculating(true);
      try {
        const data = await calculatePremium(riderId, selectedModules);
        setPremiumData(data);
      } catch (err) {
        console.error("Premium calc error", err);
      } finally {
        setCalculating(false);
      }
    };

    fetchPremium();
  }, [selectedModules, riderId]);

  const toggleModule = (moduleName) => {
    setSelectedModules(prev => 
      prev.includes(moduleName) 
        ? prev.filter(m => m !== moduleName)
        : [...prev, moduleName]
    );
  };

  const handleCreatePolicy = async () => {
    if (selectedModules.length === 0) {
      toast.error("Please select at least one coverage module.");
      return;
    }

    setCreating(true);
    try {
      await createPolicy(riderId, selectedModules);
      toast.success("Policy created successfully!");
      router.push("/dashboard");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create policy");
    } finally {
      setCreating(false);
    }
  };

  if (loadingModules) return <Loader fullScreen text="Loading coverage options..." />;

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Select Coverage</h1>
        <p className="text-gray-600 mt-2">Customize your parametric insurance. Premiums are deducted weekly from your earnings.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-8">
        <div className="md:col-span-2 space-y-4">
          {modules.map((mod) => {
            const isSelected = selectedModules.includes(mod.name);
            return (
              <div 
                key={mod.id}
                onClick={() => toggleModule(mod.name)}
                className={`p-5 rounded-xl border-2 cursor-pointer transition-all flex items-start gap-4 ${
                  isSelected 
                    ? "border-green-500 bg-green-50 ring-2 ring-green-100" 
                    : "border-gray-200 bg-white hover:border-green-300"
                }`}
              >
                <div className="pt-1">
                  <input 
                    type="checkbox" 
                    checked={isSelected}
                    readOnly
                    className="w-5 h-5 text-green-600 rounded border-gray-300 focus:ring-green-500"
                  />
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-center mb-1">
                    <h3 className="font-bold text-gray-900 text-lg">{mod.display_name}</h3>
                    <span className="font-semibold text-gray-700">₹{parseFloat(mod.base_price).toFixed(2)} / wk (base)</span>
                  </div>
                  <p className="text-sm text-gray-600">{mod.description}</p>
                  
                  <div className="mt-3 flex gap-2">
                    <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-800">
                      Trigger: {parseFloat(mod.trigger_threshold)} {mod.name === 'heat' ? '°C' : mod.name === 'rain' ? 'mm/hr' : mod.name === 'aqi' ? 'AQI' : 'mm'}
                    </span>
                    {parseFloat(mod.trigger_duration_hours) > 0 && (
                      <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-800">
                        Duration: {parseFloat(mod.trigger_duration_hours)} hr(s)
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div>
          <Card title="Premium Summary" className="sticky top-24">
            {selectedModules.length === 0 ? (
              <p className="text-gray-500 text-sm text-center py-8">Select at least one module to see premium</p>
            ) : calculating ? (
              <Loader text="Calculating premium..." />
            ) : premiumData ? (
              <div className="space-y-4">
                <div className="flex justify-between text-sm text-gray-600">
                  <span>Selected Modules ({selectedModules.length})</span>
                  <span>₹{Object.values(premiumData.module_breakdown).reduce((a, b) => a + b, 0).toFixed(2)}</span>
                </div>
                
                <div className="border-t border-gray-100 pt-3">
                  <div className="flex justify-between text-sm text-gray-600 mb-2">
                    <span>Zone Multiplier ({premiumData.zone})</span>
                    <span className={premiumData.zone_multiplier > 1 ? "text-orange-500 font-medium" : "text-green-500 font-medium"}>
                      x {premiumData.zone_multiplier}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm text-gray-600">
                    <span>Base Risk Score Discount</span>
                    <span className="text-green-600 font-medium pb-2 border-b border-gray-100 border-dashed w-full text-right">
                      Applied
                    </span>
                  </div>
                </div>

                <div className="flex justify-between items-end pt-2">
                  <span className="font-bold text-gray-900">Total Weekly Premium</span>
                  <span className="text-3xl font-extrabold text-green-600">₹{premiumData.total_weekly_premium}</span>
                </div>
                
                <button
                  onClick={handleCreatePolicy}
                  disabled={creating}
                  className="w-full mt-6 py-4 px-4 border border-transparent rounded-xl shadow-sm text-base font-bold text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 transition-all active:scale-[0.98]"
                >
                  {creating ? "Activating Policy..." : "Activate Protection"}
                </button>
                <p className="text-xs text-center text-gray-500 mt-3">By activating, you agree to auto-deduction from your weekly payouts.</p>
              </div>
            ) : null}
          </Card>
        </div>
      </div>
    </div>
  );
}
