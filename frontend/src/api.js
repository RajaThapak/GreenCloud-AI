const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
const TOKEN_KEY = 'greencloud_access_token';
const USER_KEY = 'greencloud_user';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser() {
  const value = localStorage.getItem(USER_KEY);
  return value ? JSON.parse(value) : null;
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function saveSession(data) {
  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));
}

function errorMessage(body, fallback) {
  if (body?.fields) return Object.values(body.fields).join(' ');
  if (Array.isArray(body?.detail)) return body.detail.map((item) => item.msg).join(' ');
  return body?.detail || fallback;
}

export async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  const text = await response.text();
  let body = {};
  try { body = text ? JSON.parse(text) : {}; } catch { body = { detail: text }; }

  if (response.status === 401) {
    clearSession();
    window.dispatchEvent(new Event('greencloud:unauthorized'));
  }
  if (!response.ok) {
    const error = new Error(errorMessage(body, `Request failed (${response.status}).`));
    error.status = response.status;
    error.body = body;
    throw error;
  }
  return body;
}

export const api = {
  async login(payload) {
    const data = await request('/auth/login', { method: 'POST', body: JSON.stringify(payload) });
    saveSession(data);
    return data;
  },
  async register(payload) {
    const data = await request('/auth/register', { method: 'POST', body: JSON.stringify(payload) });
    saveSession(data);
    return data;
  },
  me: () => request('/me'),
  dashboard: () => request('/dashboard'),
  workloads: (status) => request(`/workloads${status ? `?status=${encodeURIComponent(status)}` : ''}`),
  workload: (id) => request(`/workloads/${id}`),
  suggest: (payload) => request('/requirements/suggest', { method: 'POST', body: JSON.stringify(payload) }),
  createWorkload: (payload) => request('/workloads', { method: 'POST', body: JSON.stringify(payload) }),
  replan: (id, mode) => request(`/workloads/${id}/replan`, { method: 'POST', body: JSON.stringify({ mode }) }),
  approve: (id) => request(`/workloads/${id}/approve`, { method: 'POST' }),
  cancel: (id) => request(`/workloads/${id}/cancel`, { method: 'POST' }),
  reports: (months = 6) => request(`/reports?months=${months}`),
  carbon: () => request('/market/carbon'),
  settings: () => request('/settings'),
  updateSettings: (payload) => request('/settings', { method: 'PUT', body: JSON.stringify(payload) }),
};

export { API_BASE_URL };
