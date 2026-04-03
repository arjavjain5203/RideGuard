import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const registerUser = async (userData) => {
  const response = await apiClient.post('/riders/', userData);
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

export const getClaimDetails = async (claimId) => {
  const response = await apiClient.get(`/payouts/claim/${claimId}`);
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

