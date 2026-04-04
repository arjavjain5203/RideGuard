import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api';
export const ACCESS_TOKEN_STORAGE_KEY = 'rideguard_access_token';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getAccessToken = () => {
  if (typeof window === 'undefined') {
    return null;
  }
  return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
};

export const setAccessToken = (token) => {
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
  }
};

export const clearAccessToken = () => {
  if (typeof window !== 'undefined') {
    window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  }
};

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      typeof window !== 'undefined' &&
      error.response?.status === 401 &&
      getAccessToken() &&
      error.config?.url !== '/auth/login'
    ) {
      clearAccessToken();
      window.dispatchEvent(new CustomEvent('rideguard:unauthorized'));
    }
    return Promise.reject(error);
  }
);

export const extractApiErrorMessage = (error, fallback = 'Request failed') => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') {
          return item;
        }

        const field = Array.isArray(item?.loc)
          ? item.loc.filter((segment) => segment !== 'body').join('.')
          : '';
        const message = typeof item?.msg === 'string'
          ? item.msg.replace(/^Value error,\s*/i, '')
          : '';

        return [field, message].filter(Boolean).join(': ');
      })
      .filter(Boolean);

    if (messages.length > 0) {
      return messages.join(' ');
    }
  }

  const message = error?.response?.data?.message;
  if (typeof message === 'string' && message.trim()) {
    return message;
  }

  if (error?.message === 'Network Error') {
    return 'Could not reach the RideGuard API. Check that the backend server is running.';
  }

  return fallback;
};

export const extractApiFieldErrors = (error) => {
  const detail = error?.response?.data?.detail;
  if (!Array.isArray(detail) || detail.length === 0) {
    return {};
  }

  return detail.reduce((fieldErrors, item) => {
    const field = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : "";
    const message = typeof item?.msg === "string"
      ? item.msg.replace(/^Value error,\s*/i, "")
      : "";

    if (typeof field === "string" && field && message) {
      fieldErrors[field] = message;
    }
    return fieldErrors;
  }, {});
};

export const registerUser = async (userData) => {
  const response = await apiClient.post('/riders/', userData);
  return response.data;
};

export const loginUser = async (credentials) => {
  const response = await apiClient.post('/auth/login', credentials);
  return response.data;
};

export const fetchCurrentUser = async () => {
  const response = await apiClient.get('/auth/me');
  return response.data;
};

export const fetchRider = async (riderId) => {
  const response = await apiClient.get(`/riders/${riderId}`);
  return response.data;
};

export const fetchEarnings = async (riderId) => {
  const response = await apiClient.get(`/zomato/earnings/${riderId}`);
  return response.data;
};

export const fetchScore = async (riderId) => {
  const response = await apiClient.get(`/riders/${riderId}/score`);
  return response.data;
};

export const listCoverageModules = async () => {
  const response = await apiClient.get('/policies/modules');
  return response.data;
};

export const calculatePremium = async (riderId, modules) => {
  const response = await apiClient.post('/policies/calculate-premium', {
    rider_id: riderId,
    modules: modules,
  });
  return response.data;
};

export const createPolicy = async (riderId, modules) => {
  const response = await apiClient.post('/policies/', {
    rider_id: riderId,
    modules: modules,
  });
  return response.data;
};

export const updatePolicy = async (policyId, modules) => {
  const response = await apiClient.put(`/policies/${policyId}`, {
    modules: modules,
  });
  return response.data;
};

export const fetchPolicies = async (riderId) => {
  const response = await apiClient.get(`/policies/rider/${riderId}`);
  return response.data;
};

export const triggerEvent = async (triggerData) => {
  const response = await apiClient.post('/triggers/check', triggerData);
  return response.data;
};

export const fetchPayouts = async (riderId) => {
  const response = await apiClient.get(`/payouts/rider/${riderId}`);
  return response.data;
};

export const fetchClaims = async (riderId) => {
  const response = await apiClient.get(`/claims/rider/${riderId}`);
  return response.data.claims;
};

export const getClaimDetails = async (claimId) => {
  const response = await apiClient.get(`/claims/${claimId}`);
  return response.data;
};

export const processPayout = async (claimId) => {
  const response = await apiClient.post('/payouts/process', {
    claim_id: claimId,
  });
  return response.data;
};

// --- LLM ENDPOINTS ---
export const explainClaim = async (data) => {
  const response = await apiClient.post('/llm/explain-claim', data);
  return response.data;
};

export const explainRisk = async (data) => {
  const response = await apiClient.post('/llm/explain-risk', data);
  return response.data;
};

export const explainFraud = async (data) => {
  const response = await apiClient.post('/llm/explain-fraud', data);
  return response.data;
};

// --- ADMIN ENDPOINTS ---
export const fetchAdminMetrics = async () => {
  const response = await apiClient.get('/admin/metrics');
  return response.data;
};

export const fetchAdminClaims = async () => {
  const response = await apiClient.get('/admin/claims');
  return response.data;
};

export const fetchAdminFraudAlerts = async () => {
  const response = await apiClient.get('/admin/fraud-alerts');
  return response.data;
};

export const fetchAdminRiders = async () => {
  const response = await apiClient.get('/admin/riders');
  return response.data;
};

export const createAdminRider = async (userData) => {
  const response = await apiClient.post('/admin/riders', userData);
  return response.data;
};
