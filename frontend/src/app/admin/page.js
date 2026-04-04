"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FaChartLine, FaExclamationCircle, FaFileContract, FaShieldAlt, FaUserPlus, FaUsers } from "react-icons/fa";

import Card from "@/components/Card";
import { FieldError, SectionError } from "@/components/FormFeedback";
import Loader from "@/components/Loader";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import {
  createAdminRider,
  extractApiErrorMessage,
  extractApiFieldErrors,
  fetchAdminClaims,
  fetchAdminFraudAlerts,
  fetchAdminMetrics,
  fetchAdminRiders,
} from "@/services/api";
import {
  hasValidationErrors,
  mapRegisterApiMessageToFieldErrors,
  validateRegisterField,
  validateRegisterForm,
} from "@/services/validation";

const RIDER_FORM_INITIAL = {
  login_id: "",
  password: "",
  zomato_partner_id: "",
  name: "",
  phone: "",
  zone: "Koramangala",
  upi_handle: "",
};

const RIDER_FORM_EMPTY_ERRORS = {
  login_id: "",
  password: "",
  zomato_partner_id: "",
  name: "",
  phone: "",
  zone: "",
  upi_handle: "",
};

const ZONES = [
  "Koramangala",
  "Indiranagar",
  "HSR Layout",
  "Whitefield",
  "Jayanagar",
  "BTM Layout",
  "Electronic City",
  "Marathahalli",
];

const formatSignalLabel = (signalKey) =>
  String(signalKey || "")
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");

const getAlertSignalEntries = (behavioralSignals) => {
  if (!behavioralSignals || typeof behavioralSignals !== "object") {
    return [];
  }

  return Object.entries(behavioralSignals)
    .filter(([, value]) => value !== null && value !== undefined && value !== 0 && value !== "")
    .sort((left, right) => Number(right[1] || 0) - Number(left[1] || 0));
};

const formatSignalValue = (value) => {
  if (typeof value !== "number") {
    return String(value);
  }

  if (value >= 0 && value <= 1) {
    return `${Math.round(value * 100)}% risk`;
  }

  return Number.isInteger(value) ? String(value) : value.toFixed(2);
};

export default function AdminDashboard() {
  const { user, isAdmin, loading: authLoading } = useAuth();
  const router = useRouter();
  const toast = useToast();

  const [data, setData] = useState({
    metrics: null,
    claims: [],
    fraudAlerts: [],
    riders: [],
  });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [formData, setFormData] = useState(RIDER_FORM_INITIAL);
  const [errors, setErrors] = useState(RIDER_FORM_EMPTY_ERRORS);
  const [touched, setTouched] = useState({});
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [formError, setFormError] = useState("");
  const [creatingRider, setCreatingRider] = useState(false);

  const loadAdminData = useCallback(async () => {
    try {
      const [metrics, claims, fraudAlerts, riders] = await Promise.all([
        fetchAdminMetrics(),
        fetchAdminClaims(),
        fetchAdminFraudAlerts(),
        fetchAdminRiders(),
      ]);
      setData({ metrics, claims, fraudAlerts, riders });
      setLoadError("");
    } catch (err) {
      console.error("Admin data load failed", err);
      setLoadError("Failed to load admin data. Refresh the page and try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push("/admin/login");
      return;
    }
    if (!isAdmin) {
      router.push("/dashboard");
      return;
    }

    loadAdminData();
  }, [authLoading, isAdmin, loadAdminData, router, user]);

  const getFieldError = (name) => (touched[name] || submitAttempted ? errors[name] : "");
  const hasFieldError = (name) => Boolean(getFieldError(name));
  const getInputClassName = (name) =>
    `mt-1 block w-full rounded-lg shadow-sm bg-gray-50 border p-3 ${
      hasFieldError(name)
        ? "border-red-300 focus:border-red-500 focus:ring-red-500"
        : "border-gray-300 focus:border-emerald-500 focus:ring-emerald-500"
    }`;

  const resetForm = () => {
    setFormData(RIDER_FORM_INITIAL);
    setErrors(RIDER_FORM_EMPTY_ERRORS);
    setTouched({});
    setSubmitAttempted(false);
    setFormError("");
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    const nextValue = name === "phone" ? value.replace(/\D/g, "").slice(0, 10) : value;

    setFormData((current) => ({ ...current, [name]: nextValue }));
    setFormError("");

    if (touched[name] || submitAttempted) {
      setErrors((current) => ({
        ...current,
        [name]: validateRegisterField(name, nextValue, ZONES),
      }));
    }
  };

  const handleBlur = (event) => {
    const { name } = event.target;
    setTouched((current) => ({ ...current, [name]: true }));
    setErrors((current) => ({
      ...current,
      [name]: validateRegisterField(name, formData[name], ZONES),
    }));
  };

  const applyApiErrors = (error) => {
    const backendFieldErrors = extractApiFieldErrors(error);
    const message = extractApiErrorMessage(error, "Failed to create rider");
    const mappedFieldErrors = {
      ...backendFieldErrors,
      ...mapRegisterApiMessageToFieldErrors(message),
    };

    if (Object.keys(mappedFieldErrors).length > 0) {
      setErrors((current) => ({ ...current, ...mappedFieldErrors }));
      setTouched((current) => ({
        ...current,
        ...Object.fromEntries(Object.keys(mappedFieldErrors).map((fieldName) => [fieldName, true])),
      }));
      return;
    }

    setFormError(message);
  };

  const handleCreateRider = async (event) => {
    event.preventDefault();
    setSubmitAttempted(true);
    setFormError("");

    const nextErrors = validateRegisterForm(formData, ZONES);
    setErrors(nextErrors);
    if (hasValidationErrors(nextErrors)) {
      return;
    }

    setCreatingRider(true);
    try {
      const createdRider = await createAdminRider(formData);
      setData((current) => ({
        ...current,
        riders: [createdRider, ...current.riders.filter((rider) => rider.id !== createdRider.id)],
      }));
      resetForm();
      toast.success("Rider added successfully.");

      try {
        const [metrics, riders] = await Promise.all([fetchAdminMetrics(), fetchAdminRiders()]);
        setData((current) => ({ ...current, metrics, riders }));
      } catch (refreshError) {
        console.error("Admin refresh after rider create failed", refreshError);
      }
    } catch (error) {
      applyApiErrors(error);
    } finally {
      setCreatingRider(false);
    }
  };

  if (authLoading || loading) return <Loader fullScreen text="Loading Admin Dashboard..." />;

  const { metrics, claims, fraudAlerts, riders } = data;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="space-y-6">
        <div className="mb-6 rounded-2xl bg-slate-950 px-8 py-6 text-white">
          <p className="text-sm uppercase tracking-[0.3em] text-emerald-300">Operations Console</p>
          <h1 className="mt-2 text-3xl font-bold">Admin Dashboard</h1>
          <p className="mt-1 text-slate-300">System observability, fraud monitoring, and rider management for RideGuard operations.</p>
        </div>

        <SectionError message={loadError} />

        {metrics && (
          <div className="grid md:grid-cols-4 gap-4 mb-8">
            <Card>
              <div className="flex items-center gap-2 mb-2 text-blue-600">
                <FaFileContract />
                <h3 className="font-semibold text-sm">Active Policies</h3>
              </div>
              <p className="text-2xl font-bold">{metrics.active_policies}</p>
            </Card>
            <Card>
              <div className="flex items-center gap-2 mb-2 text-green-600">
                <FaChartLine />
                <h3 className="font-semibold text-sm">Weekly Premiums</h3>
              </div>
              <p className="text-2xl font-bold">₹{metrics.total_premiums_weekly}</p>
            </Card>
            <Card>
              <div className="flex items-center gap-2 mb-2 text-orange-600">
                <FaShieldAlt />
                <h3 className="font-semibold text-sm">Loss Ratio</h3>
              </div>
              <p className="text-2xl font-bold">{metrics.loss_ratio.toFixed(2)}</p>
            </Card>
            <Card>
              <div className="flex items-center gap-2 mb-2 text-purple-600">
                <FaShieldAlt />
                <h3 className="font-semibold text-sm">Avg Trust Score</h3>
              </div>
              <p className="text-2xl font-bold">{metrics.avg_urts}</p>
            </Card>
          </div>
        )}

        <div className="grid xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] gap-6">
          <Card>
            <div className="flex items-center gap-2 mb-4 text-emerald-700">
              <FaUserPlus />
              <h3 className="font-bold text-gray-900">Add Rider</h3>
            </div>

            <form className="space-y-4" onSubmit={handleCreateRider} noValidate>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Login ID</label>
                  <input
                    name="login_id"
                    type="text"
                    value={formData.login_id}
                    aria-invalid={hasFieldError("login_id")}
                    aria-describedby={hasFieldError("login_id") ? "admin-rider-login-id-error" : undefined}
                    className={getInputClassName("login_id")}
                    placeholder="rider.new@rideguard.local"
                    onChange={handleChange}
                    onBlur={handleBlur}
                  />
                  <FieldError id="admin-rider-login-id-error" message={getFieldError("login_id")} />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Password</label>
                  <input
                    name="password"
                    type="password"
                    value={formData.password}
                    aria-invalid={hasFieldError("password")}
                    aria-describedby={hasFieldError("password") ? "admin-rider-password-error" : undefined}
                    className={getInputClassName("password")}
                    placeholder="At least 8 characters"
                    onChange={handleChange}
                    onBlur={handleBlur}
                  />
                  <FieldError id="admin-rider-password-error" message={getFieldError("password")} />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Zomato Partner ID</label>
                  <input
                    name="zomato_partner_id"
                    type="text"
                    value={formData.zomato_partner_id}
                    aria-invalid={hasFieldError("zomato_partner_id")}
                    aria-describedby={hasFieldError("zomato_partner_id") ? "admin-rider-zomato-id-error" : undefined}
                    className={getInputClassName("zomato_partner_id")}
                    placeholder="ZMT-BLR-9001"
                    onChange={handleChange}
                    onBlur={handleBlur}
                  />
                  <FieldError id="admin-rider-zomato-id-error" message={getFieldError("zomato_partner_id")} />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Full Name</label>
                  <input
                    name="name"
                    type="text"
                    value={formData.name}
                    aria-invalid={hasFieldError("name")}
                    aria-describedby={hasFieldError("name") ? "admin-rider-name-error" : undefined}
                    className={getInputClassName("name")}
                    placeholder="Rider Name"
                    onChange={handleChange}
                    onBlur={handleBlur}
                  />
                  <FieldError id="admin-rider-name-error" message={getFieldError("name")} />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Phone Number</label>
                  <input
                    name="phone"
                    type="tel"
                    inputMode="numeric"
                    value={formData.phone}
                    aria-invalid={hasFieldError("phone")}
                    aria-describedby={hasFieldError("phone") ? "admin-rider-phone-error" : undefined}
                    className={getInputClassName("phone")}
                    placeholder="9876543210"
                    onChange={handleChange}
                    onBlur={handleBlur}
                  />
                  <FieldError id="admin-rider-phone-error" message={getFieldError("phone")} />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Primary Delivery Zone</label>
                  <select
                    name="zone"
                    value={formData.zone}
                    aria-invalid={hasFieldError("zone")}
                    aria-describedby={hasFieldError("zone") ? "admin-rider-zone-error" : undefined}
                    className={getInputClassName("zone")}
                    onChange={handleChange}
                    onBlur={handleBlur}
                  >
                    {ZONES.map((zone) => (
                      <option key={zone} value={zone}>{zone}</option>
                    ))}
                  </select>
                  <FieldError id="admin-rider-zone-error" message={getFieldError("zone")} />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">UPI Handle</label>
                <input
                  name="upi_handle"
                  type="text"
                  value={formData.upi_handle}
                  aria-invalid={hasFieldError("upi_handle")}
                  aria-describedby={hasFieldError("upi_handle") ? "admin-rider-upi-error" : undefined}
                  className={getInputClassName("upi_handle")}
                  placeholder="rider@ybl"
                  onChange={handleChange}
                  onBlur={handleBlur}
                />
                <FieldError id="admin-rider-upi-error" message={getFieldError("upi_handle")} />
              </div>

              <SectionError message={formError} />

              <button
                type="submit"
                disabled={creatingRider}
                className="w-full rounded-lg bg-emerald-600 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:opacity-50"
              >
                {creatingRider ? "Adding Rider..." : "Add Rider"}
              </button>
            </form>
          </Card>

          <Card>
            <div className="flex items-center gap-2 mb-4 text-slate-700">
              <FaUsers />
              <h3 className="font-bold text-gray-900">Riders</h3>
              <span className="ml-auto rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                {riders.length}
              </span>
            </div>

            {riders.length === 0 ? (
              <p className="text-sm text-gray-500">No riders have been added yet.</p>
            ) : (
              <div className="space-y-3 max-h-[32rem] overflow-y-auto pr-1">
                {riders.map((rider) => (
                  <div key={rider.id} className="rounded-xl border border-gray-100 bg-gray-50 px-4 py-3">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="font-semibold text-gray-900">{rider.name}</p>
                        <p className="text-sm text-gray-500">{rider.login_id}</p>
                        <p className="text-xs text-gray-500 mt-1">Partner ID: {rider.zomato_partner_id}</p>
                      </div>
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                          rider.is_active ? "bg-green-100 text-green-700" : "bg-gray-200 text-gray-700"
                        }`}
                      >
                        {rider.is_active ? "Active" : "Inactive"}
                      </span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-600">
                      <span className="rounded-full bg-white px-2.5 py-1 border border-gray-200">Zone: {rider.zone}</span>
                      <span className="rounded-full bg-white px-2.5 py-1 border border-gray-200">URTS: {rider.base_urts}</span>
                      <span className="rounded-full bg-white px-2.5 py-1 border border-gray-200">UPI: {rider.upi_handle}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <Card>
            <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
              <FaExclamationCircle className="text-red-500" /> Fraud Alerts
            </h3>
            {fraudAlerts.length === 0 ? (
              <p className="text-sm text-gray-500">No recent fraud alerts.</p>
            ) : (
              <div className="space-y-3">
                {fraudAlerts.map((alert) => (
                  <div key={alert.claim_id} className="rounded-lg border border-red-100 bg-red-50 p-3 text-sm">
                    <div className="flex items-start justify-between gap-3 font-bold text-red-800">
                      <div>
                        <p>Rider {alert.rider_id.substring(0, 8)}</p>
                        <p className="mt-1 text-xs font-medium text-red-600">
                          {new Date(alert.created_at).toLocaleString()}
                        </p>
                      </div>
                      <span>URTS: {alert.effective_urts}</span>
                    </div>
                    {getAlertSignalEntries(alert.behavioral_signals).length === 0 ? (
                      <p className="mt-2 text-xs text-red-600">Behavioral anomaly detected, but no detailed signal values were recorded.</p>
                    ) : (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {getAlertSignalEntries(alert.behavioral_signals).map(([signalKey, value]) => (
                          <span
                            key={`${alert.claim_id}-${signalKey}`}
                            className="rounded-full border border-red-200 bg-white px-2.5 py-1 text-xs font-medium text-red-700"
                          >
                            {formatSignalLabel(signalKey)}: {formatSignalValue(value)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card>
            <h3 className="font-bold text-gray-900 mb-4">Recent Claims</h3>
            {claims.length === 0 ? (
              <p className="text-sm text-gray-500">No recent claims.</p>
            ) : (
              <div className="space-y-3">
                {claims.map((claim) => (
                  <div key={claim.id} className="flex justify-between items-center border-b pb-2 text-sm">
                    <div>
                      <p className="font-medium text-gray-800">Rider {claim.rider_id.substring(0, 8)}</p>
                      <p className="text-xs text-gray-500">{new Date(claim.created_at).toLocaleString()}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-gray-900">₹{claim.loss_amount}</p>
                      <span className={`text-xs px-2 py-0.5 rounded uppercase font-bold ${
                        claim.status === "paid"
                          ? "bg-green-100 text-green-700"
                          : claim.status === "capped"
                            ? "bg-orange-100 text-orange-700"
                            : "bg-gray-100 text-gray-700"
                      }`}>
                        {claim.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
