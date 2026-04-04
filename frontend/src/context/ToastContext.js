"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

const ToastContext = createContext(null);

const DEFAULT_DURATIONS = {
  success: 3000,
  error: 4000,
  custom: 6000,
};

function ToastViewport({ toasts, dismiss }) {
  return (
    <div
      aria-atomic="false"
      aria-live="polite"
      className="pointer-events-none fixed top-4 right-4 z-[9999] flex w-full max-w-sm flex-col gap-3"
    >
      {toasts.map((toast) => {
        if (toast.type === "custom" && typeof toast.render === "function") {
          return (
            <div key={toast.id} className="pointer-events-auto">
              {toast.render({ id: toast.id, dismiss: () => dismiss(toast.id) })}
            </div>
          );
        }

        return (
          <div
            key={toast.id}
            role={toast.type === "error" ? "alert" : "status"}
            className={`pointer-events-auto rounded-xl border px-4 py-3 shadow-lg backdrop-blur ${
              toast.type === "error"
                ? "border-red-200 bg-red-50 text-red-800"
                : "border-green-200 bg-white text-gray-900"
            }`}
          >
            <div className="flex items-start gap-3">
              <div
                className={`mt-0.5 h-2.5 w-2.5 shrink-0 rounded-full ${
                  toast.type === "error" ? "bg-red-500" : "bg-green-500"
                }`}
              />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">{toast.message}</p>
              </div>
              <button
                type="button"
                aria-label="Dismiss notification"
                onClick={() => dismiss(toast.id)}
                className="text-xs font-semibold text-gray-500 hover:text-gray-800"
              >
                Close
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timersRef = useRef(new Map());
  const nextIdRef = useRef(1);

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const scheduleDismiss = useCallback((id, duration) => {
    if (!Number.isFinite(duration) || duration <= 0) {
      return;
    }
    const timer = setTimeout(() => dismiss(id), duration);
    timersRef.current.set(id, timer);
  }, [dismiss]);

  const addToast = useCallback((toastInput, options = {}) => {
    const id = `toast-${nextIdRef.current++}`;
    const type = options.type || "success";
    const duration = options.duration ?? DEFAULT_DURATIONS[type] ?? 4000;
    const nextToast = {
      id,
      type,
      duration,
      message: typeof toastInput === "string" ? toastInput : "",
      render: type === "custom" ? toastInput : null,
    };

    setToasts((current) => [...current, nextToast]);
    scheduleDismiss(id, duration);
    return id;
  }, [scheduleDismiss]);

  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      timers.forEach((timer) => clearTimeout(timer));
      timers.clear();
    };
  }, []);

  const toast = useMemo(
    () => ({
      success: (message, options) => addToast(message, { ...options, type: "success" }),
      error: (message, options) => addToast(message, { ...options, type: "error" }),
      custom: (render, options) => addToast(render, { ...options, type: "custom" }),
      dismiss,
    }),
    [addToast, dismiss]
  );

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <ToastViewport toasts={toasts} dismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
