"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FieldError, SectionError } from "@/components/FormFeedback";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { extractApiErrorMessage, extractApiFieldErrors, loginUser, registerUser } from "@/services/api";
import {
  hasValidationErrors,
  mapRegisterApiMessageToFieldErrors,
  validateRegisterField,
  validateRegisterForm,
} from "@/services/validation";

const INITIAL_FORM_DATA = {
  login_id: "",
  password: "",
  zomato_partner_id: "",
  name: "",
  phone: "",
  zone: "Koramangala",
  upi_handle: "",
};

const EMPTY_ERRORS = {
  login_id: "",
  password: "",
  zomato_partner_id: "",
  name: "",
  phone: "",
  zone: "",
  upi_handle: "",
};

const zones = ["Koramangala", "Indiranagar", "HSR Layout", "Whitefield", "Jayanagar", "BTM Layout"];

export default function Register() {
  const [formData, setFormData] = useState(INITIAL_FORM_DATA);
  const [errors, setErrors] = useState(EMPTY_ERRORS);
  const [touched, setTouched] = useState({});
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { login } = useAuth();
  const toast = useToast();

  const handleChange = (e) => {
    const { name, value } = e.target;
    const nextValue = name === "phone" ? value.replace(/\D/g, "").slice(0, 10) : value;

    setFormData((current) => ({ ...current, [name]: nextValue }));
    setFormError("");

    if (touched[name] || submitAttempted) {
      setErrors((current) => ({
        ...current,
        [name]: validateRegisterField(name, nextValue, zones),
      }));
    }
  };

  const handleBlur = (e) => {
    const { name } = e.target;
    setTouched((current) => ({ ...current, [name]: true }));
    setErrors((current) => ({
      ...current,
      [name]: validateRegisterField(name, formData[name], zones),
    }));
  };

  const getFieldError = (name) => (touched[name] || submitAttempted ? errors[name] : "");
  const hasFieldError = (name) => Boolean(getFieldError(name));
  const getInputClassName = (name) =>
    `mt-1 block w-full rounded-lg shadow-sm bg-gray-50 border p-3 ${
      hasFieldError(name)
        ? "border-red-300 focus:border-red-500 focus:ring-red-500"
        : "border-gray-300 focus:border-green-500 focus:ring-green-500"
    }`;

  const applyApiErrors = (err) => {
    const backendFieldErrors = extractApiFieldErrors(err);
    const message = extractApiErrorMessage(err, "Registration failed");
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitAttempted(true);
    setFormError("");

    const nextErrors = validateRegisterForm(formData, zones);
    setErrors(nextErrors);
    if (hasValidationErrors(nextErrors)) {
      return;
    }

    setLoading(true);
    try {
      await registerUser(formData);
    } catch (err) {
      applyApiErrors(err);
      setLoading(false);
      return;
    }

    try {
      const authResponse = await loginUser({
        login_id: formData.login_id,
        password: formData.password,
      });
      login(authResponse);
      toast.success("Registration successful!");
      router.push("/onboarding");
    } catch (err) {
      toast.error(
        `Registration completed, but automatic sign-in failed. ${extractApiErrorMessage(
          err,
          "Please sign in manually."
        )}`
      );
      router.push("/login");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-gray-100 p-8">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-extrabold text-gray-900">Partner Registration</h2>
          <p className="mt-2 text-sm text-gray-600">Join RideGuard and protect your income.</p>
        </div>
        <form className="space-y-6" onSubmit={handleSubmit} noValidate>
          <div>
            <label className="block text-sm font-medium text-gray-700">Login ID</label>
            <input
              name="login_id"
              type="text"
              required
              value={formData.login_id}
              aria-invalid={hasFieldError("login_id")}
              aria-describedby={hasFieldError("login_id") ? "login-id-error" : undefined}
              className={getInputClassName("login_id")}
              placeholder="yourname@rideguard"
              onChange={handleChange}
              onBlur={handleBlur}
            />
            <FieldError id="login-id-error" message={getFieldError("login_id")} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input
              name="password"
              type="password"
              required
              minLength={8}
              value={formData.password}
              aria-invalid={hasFieldError("password")}
              aria-describedby={hasFieldError("password") ? "password-error" : undefined}
              className={getInputClassName("password")}
              placeholder="At least 8 characters with letters and numbers"
              onChange={handleChange}
              onBlur={handleBlur}
            />
            <FieldError id="password-error" message={getFieldError("password")} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Zomato Partner ID</label>
            <input
              name="zomato_partner_id"
              type="text"
              required
              value={formData.zomato_partner_id}
              aria-invalid={hasFieldError("zomato_partner_id")}
              aria-describedby={hasFieldError("zomato_partner_id") ? "zomato-partner-id-error" : undefined}
              className={getInputClassName("zomato_partner_id")}
              placeholder="e.g. ZMT-BLR-1234"
              onChange={handleChange}
              onBlur={handleBlur}
            />
            <FieldError id="zomato-partner-id-error" message={getFieldError("zomato_partner_id")} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Full Name</label>
            <input
              name="name"
              type="text"
              required
              value={formData.name}
              aria-invalid={hasFieldError("name")}
              aria-describedby={hasFieldError("name") ? "full-name-error" : undefined}
              className={getInputClassName("name")}
              placeholder="John Doe"
              onChange={handleChange}
              onBlur={handleBlur}
            />
            <FieldError id="full-name-error" message={getFieldError("name")} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Phone Number</label>
            <input
              name="phone"
              type="tel"
              required
              inputMode="numeric"
              pattern="[0-9]{10}"
              minLength={10}
              maxLength={10}
              title="Phone number must be exactly 10 digits"
              value={formData.phone}
              aria-invalid={hasFieldError("phone")}
              aria-describedby="phone-error"
              className={getInputClassName("phone")}
              placeholder="9876543210"
              onChange={handleChange}
              onBlur={handleBlur}
            />
            <FieldError id="phone-error" message={getFieldError("phone")} />
            {!hasFieldError("phone") && <p className="mt-2 text-xs text-gray-500">Enter a 10-digit mobile number.</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Primary Delivery Zone</label>
            <select
              name="zone"
              aria-invalid={hasFieldError("zone")}
              aria-describedby={hasFieldError("zone") ? "zone-error" : undefined}
              className={getInputClassName("zone")}
              value={formData.zone}
              onChange={handleChange}
              onBlur={handleBlur}
            >
              {zones.map((z) => (
                <option key={z} value={z}>{z}</option>
              ))}
            </select>
            <FieldError id="zone-error" message={getFieldError("zone")} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">UPI Handle</label>
            <input
              name="upi_handle"
              type="text"
              required
              value={formData.upi_handle}
              aria-invalid={hasFieldError("upi_handle")}
              aria-describedby={hasFieldError("upi_handle") ? "upi-handle-error" : undefined}
              className={getInputClassName("upi_handle")}
              placeholder="john@zomato"
              onChange={handleChange}
              onBlur={handleBlur}
            />
            <FieldError id="upi-handle-error" message={getFieldError("upi_handle")} />
          </div>
          <SectionError message={formError} />
          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors disabled:opacity-50"
          >
            {loading ? "Registering..." : "Complete Registration"}
          </button>
        </form>
      </div>
    </div>
  );
}
