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

export default function Login() {
  const [formData, setFormData] = useState(INITIAL_FORM_DATA);
  const [errors, setErrors] = useState(EMPTY_ERRORS);
  const [touched, setTouched] = useState({});
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { login, getDefaultRedirectPath } = useAuth();
  const toast = useToast();

  const getFieldError = (name) => (touched[name] || submitAttempted ? errors[name] : "");
  const hasFieldError = (name) => Boolean(getFieldError(name));
  const getInputClassName = (name) =>
    `mt-1 block w-full rounded-lg shadow-sm bg-gray-50 border p-3 ${
      hasFieldError(name)
        ? "border-red-300 focus:border-red-500 focus:ring-red-500"
        : "border-gray-300 focus:border-green-500 focus:ring-green-500"
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

  const handleSubmit = async (e) => {
    e.preventDefault();
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
      login(authResponse);
      toast.success(`Welcome back, ${authResponse.user.name}!`);
      router.push(getDefaultRedirectPath(authResponse.user.role));
    } catch (err) {
      setFormError(extractApiErrorMessage(err, "Login failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-gray-100 p-8">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-extrabold text-gray-900">Rider Login</h2>
          <p className="mt-2 text-sm text-gray-600">Sign in with your RideGuard login ID and password.</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-6" noValidate>
          <div>
            <label className="block text-sm font-medium text-gray-700">Login ID</label>
            <input
              name="login_id"
              type="text"
              required
              aria-invalid={hasFieldError("login_id")}
              aria-describedby={hasFieldError("login_id") ? "rider-login-id-error" : undefined}
              className={getInputClassName("login_id")}
              placeholder="rider.demo@rideguard.local"
              value={formData.login_id}
              onChange={handleChange}
              onBlur={handleBlur}
            />
            <FieldError id="rider-login-id-error" message={getFieldError("login_id")} />
            <p className="mt-2 text-xs text-gray-500">
              Legacy riders created before this update can use their Zomato Partner ID as the login ID.
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input
              name="password"
              type="password"
              required
              aria-invalid={hasFieldError("password")}
              aria-describedby={hasFieldError("password") ? "rider-password-error" : undefined}
              className={getInputClassName("password")}
              placeholder="Enter your password"
              value={formData.password}
              onChange={handleChange}
              onBlur={handleBlur}
            />
            <FieldError id="rider-password-error" message={getFieldError("password")} />
            <p className="mt-2 text-xs text-gray-500">
              Legacy riders can use their registered phone number as the temporary password.
            </p>
          </div>
          <SectionError message={formError} />
          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 transition-colors disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Access Dashboard"}
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-gray-500">
          Need admin access?{" "}
          <Link href="/admin/login" className="font-semibold text-green-600 hover:text-green-700">
            Go to admin login
          </Link>
        </p>
      </div>
    </div>
  );
}
