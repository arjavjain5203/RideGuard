"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FieldError, SectionError } from "@/components/FormFeedback";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { extractApiErrorMessage, loginUser } from "@/services/api";
import { hasValidationErrors, validateAuthField, validateAuthForm } from "@/services/validation";

const INITIAL_FORM_DATA = {
  login_id: "",
  password: "",
};

const EMPTY_ERRORS = {
  login_id: "",
  password: "",
};

export default function AdminLoginPage() {
  const [formData, setFormData] = useState(INITIAL_FORM_DATA);
  const [errors, setErrors] = useState(EMPTY_ERRORS);
  const [touched, setTouched] = useState({});
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { login } = useAuth();
  const toast = useToast();

  const getFieldError = (name) => (touched[name] || submitAttempted ? errors[name] : "");
  const hasFieldError = (name) => Boolean(getFieldError(name));
  const getInputClassName = (name) =>
    `mt-1 block w-full rounded-lg bg-slate-950 p-3 text-white shadow-sm border ${
      hasFieldError(name)
        ? "border-red-400 focus:border-red-400 focus:ring-red-400"
        : "border-slate-700 focus:border-emerald-500 focus:ring-emerald-500"
    }`;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((current) => ({ ...current, [name]: value }));
    setFormError("");

    if (touched[name] || submitAttempted) {
      setErrors((current) => ({
        ...current,
        [name]: validateAuthField(name, value),
      }));
    }
  };

  const handleBlur = (e) => {
    const { name } = e.target;
    setTouched((current) => ({ ...current, [name]: true }));
    setErrors((current) => ({
      ...current,
      [name]: validateAuthField(name, formData[name]),
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitAttempted(true);
    setFormError("");

    const nextErrors = validateAuthForm(formData);
    setErrors(nextErrors);
    if (hasValidationErrors(nextErrors)) {
      return;
    }

    setLoading(true);
    try {
      const authResponse = await loginUser(formData);
      if (authResponse.user.role !== "admin") {
        setFormError("This account does not have admin access.");
        return;
      }
      login(authResponse);
      toast.success("Admin session started.");
      router.push("/admin");
    } catch (err) {
      setFormError(extractApiErrorMessage(err, "Admin login failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center bg-slate-950 px-4 py-12">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-8 shadow-2xl shadow-slate-950/40">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white">Admin Panel</h1>
          <p className="mt-2 text-sm text-slate-400">Restricted access for operations and fraud monitoring.</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-6" noValidate>
          <div>
            <label className="block text-sm font-medium text-slate-200">Admin Login ID</label>
            <input
              name="login_id"
              type="text"
              required
              aria-invalid={hasFieldError("login_id")}
              aria-describedby={hasFieldError("login_id") ? "admin-login-id-error" : undefined}
              className={getInputClassName("login_id")}
              placeholder="admin@rideguard.local"
              value={formData.login_id}
              onChange={handleChange}
              onBlur={handleBlur}
            />
            <FieldError id="admin-login-id-error" message={getFieldError("login_id")} />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-200">Password</label>
            <input
              name="password"
              type="password"
              required
              aria-invalid={hasFieldError("password")}
              aria-describedby={hasFieldError("password") ? "admin-password-error" : undefined}
              className={getInputClassName("password")}
              placeholder="Enter admin password"
              value={formData.password}
              onChange={handleChange}
              onBlur={handleBlur}
            />
            <FieldError id="admin-password-error" message={getFieldError("password")} />
          </div>
          <SectionError message={formError} />
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-emerald-500 px-4 py-3 text-sm font-semibold text-slate-950 transition-colors hover:bg-emerald-400 disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Open Admin Panel"}
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-400">
          Rider account?{" "}
          <Link href="/login" className="font-semibold text-emerald-400 hover:text-emerald-300">
            Go to rider login
          </Link>
        </p>
      </div>
    </div>
  );
}
