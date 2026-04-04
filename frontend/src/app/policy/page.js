"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { SectionError } from "@/components/FormFeedback";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import {
  calculatePremium,
  createPolicy,
  extractApiErrorMessage,
  fetchPolicies,
  listCoverageModules,
  updatePolicy,
} from "@/services/api";
import Loader from "@/components/Loader";
import Card from "@/components/Card";

const normalizeModuleSelection = (modules) => {
  if (!Array.isArray(modules)) {
    return [];
  }

  return modules
    .map((module) => String(module || "").trim().toLowerCase())
    .filter(Boolean)
    .filter((module, index, values) => values.indexOf(module) === index);
};

const selectionsMatch = (left, right) => {
  const normalizedLeft = [...normalizeModuleSelection(left)].sort();
  const normalizedRight = [...normalizeModuleSelection(right)].sort();

  return JSON.stringify(normalizedLeft) === JSON.stringify(normalizedRight);
};

export default function PolicySelection() {
  const { riderId, user, isRider, loading: authLoading } = useAuth();
  const toast = useToast();
  const router = useRouter();
  
  const [modules, setModules] = useState([]);
  const [selectedModules, setSelectedModules] = useState([]);
  const [activePolicy, setActivePolicy] = useState(null);
  const [premiumData, setPremiumData] = useState(null);
  const [modulesError, setModulesError] = useState("");
  const [premiumError, setPremiumError] = useState("");
  const [selectionError, setSelectionError] = useState("");
  const [actionError, setActionError] = useState("");
  
  const [loadingModules, setLoadingModules] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [creating, setCreating] = useState(false);

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

    const loadPolicyPage = async () => {
      try {
        const [moduleData, existingPolicies] = await Promise.all([
          listCoverageModules(),
          fetchPolicies(riderId).catch(() => []),
        ]);

        const active = existingPolicies.find((policy) => policy.status === "active") || null;
        const initialSelection = normalizeModuleSelection(active?.modules);

        setModules(moduleData);
        setActivePolicy(active);
        setModulesError("");
        setSelectedModules(
          initialSelection.length > 0
            ? initialSelection
            : [moduleData[0]?.name, moduleData[1]?.name].filter(Boolean)
        );
      } catch (err) {
        setModules([]);
        setActivePolicy(null);
        setModulesError("Failed to load coverage modules. Refresh the page and try again.");
      } finally {
        setLoadingModules(false);
      }
    };

    loadPolicyPage();
  }, [authLoading, isRider, riderId, router, user]);

  // Recalculate premium when selection changes
  useEffect(() => {
    if (selectedModules.length === 0) {
      setPremiumData(null);
      setPremiumError("");
      return;
    }
    
    const fetchPremium = async () => {
      setCalculating(true);
      try {
        const data = await calculatePremium(riderId, selectedModules);
        setPremiumData(data);
        setPremiumError("");
      } catch (err) {
        setPremiumData(null);
        setPremiumError(extractApiErrorMessage(err, "Failed to calculate premium for the selected modules."));
      } finally {
        setCalculating(false);
      }
    };

    fetchPremium();
  }, [selectedModules, riderId]);

  const toggleModule = (moduleName) => {
    setSelectedModules((prev) => {
      const nextSelection = prev.includes(moduleName)
        ? prev.filter((module) => module !== moduleName)
        : [...prev, moduleName];

      if (nextSelection.length > 0) {
        setSelectionError("");
      }
      setActionError("");
      return nextSelection;
    });
  };

  const handleCreatePolicy = async () => {
    if (selectedModules.length === 0) {
      setSelectionError("Select at least one coverage module before activating protection.");
      setActionError("");
      return;
    }

    setCreating(true);
    setSelectionError("");
    setActionError("");
    try {
      const nextPolicy = activePolicy
        ? await updatePolicy(activePolicy.id, selectedModules)
        : await createPolicy(riderId, selectedModules);
      setActivePolicy(nextPolicy);
      setSelectedModules(normalizeModuleSelection(nextPolicy.modules));
      toast.success(activePolicy ? "Coverage updated successfully!" : "Policy created successfully!");
    } catch (err) {
      setActionError(
        extractApiErrorMessage(err, activePolicy ? "Failed to update coverage" : "Failed to create policy")
      );
    } finally {
      setCreating(false);
    }
  };

  const hasActivePolicy = Boolean(activePolicy);
  const hasCoverageChanges = hasActivePolicy && !selectionsMatch(activePolicy.modules, selectedModules);
  const actionButtonLabel = creating
    ? hasActivePolicy
      ? "Saving Coverage..."
      : "Activating Policy..."
    : hasActivePolicy
      ? "Save Coverage Changes"
      : "Activate Protection";

  if (authLoading || loadingModules) return <Loader fullScreen text="Loading coverage options..." />;

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">{hasActivePolicy ? "Manage Coverage" : "Select Coverage"}</h1>
        <p className="text-gray-600 mt-2">
          {hasActivePolicy
            ? "Add or remove coverage modules on your active policy and save the changes here."
            : "Customize your parametric insurance. Premiums are deducted weekly from your earnings."}
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-8">
        <div className="md:col-span-2 space-y-4">
          <SectionError message={modulesError} />
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
            {hasActivePolicy && (
              <div className="mb-4 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-900">
                <p className="font-semibold">Active Policy</p>
                <p className="mt-1">Saved modules: {normalizeModuleSelection(activePolicy.modules).join(", ") || "None"}</p>
                <p className="mt-1">Current weekly premium: ₹{activePolicy.weekly_premium}</p>
                <p className="mt-1 text-blue-700">
                  {hasCoverageChanges
                    ? "You have unsaved coverage changes."
                    : "Your saved coverage is shown below. Update the selection to change it."}
                </p>
              </div>
            )}
            {selectedModules.length === 0 ? (
              <div className="space-y-4 py-8">
                <p className="text-gray-500 text-sm text-center">Select at least one module to see premium</p>
                <SectionError message={selectionError} className="mx-2" />
              </div>
            ) : calculating ? (
              <Loader text="Calculating premium..." />
            ) : premiumError ? (
              <div className="space-y-4 py-2">
                <SectionError message={premiumError} />
                <p className="text-sm text-gray-500">Adjust your selection or try again.</p>
              </div>
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
                <SectionError message={actionError} />
                
                <button
                  onClick={handleCreatePolicy}
                  disabled={creating || calculating || !premiumData || (hasActivePolicy && !hasCoverageChanges)}
                  className="w-full mt-6 py-4 px-4 border border-transparent rounded-xl shadow-sm text-base font-bold text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 transition-all active:scale-[0.98]"
                >
                  {actionButtonLabel}
                </button>
                <p className="text-xs text-center text-gray-500 mt-3">
                  {hasActivePolicy
                    ? "Changes apply to your existing active policy once saved."
                    : "By activating, you agree to auto-deduction from your weekly payouts."}
                </p>
              </div>
            ) : null}
          </Card>
        </div>
      </div>
    </div>
  );
}
