// API client helper
export const API_BASE = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV
  ? 'http://localhost:8000'
  : 'https://brochat-gxkm.onrender.com');

async function apiFetch(path, options = {}) {
  const token = localStorage.getItem('brochat_token');
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    localStorage.removeItem('brochat_token');
    window.location.href = '/login';
    return;
  }
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

export const api = {
  signup: (data) => apiFetch('/api/auth/signup', { method: 'POST', body: JSON.stringify(data) }),
  login: (data) => apiFetch('/api/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  me: () => apiFetch('/api/auth/me'),
  getBots: () => apiFetch('/api/bots'),
  createBot: (data) => apiFetch('/api/bots', { method: 'POST', body: JSON.stringify(data) }),
  getBot: (id) => apiFetch(`/api/bots/${id}`),
  updateBot: (id, data) => apiFetch(`/api/bots/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteBot: (id) => apiFetch(`/api/bots/${id}`, { method: 'DELETE' }),
  getSources: (botId) => apiFetch(`/api/bots/${botId}/sources`),
  addSource: (botId, data) => apiFetch(`/api/bots/${botId}/sources`, { method: 'POST', body: JSON.stringify(data) }),
  deleteSource: (botId, sourceId) => apiFetch(`/api/bots/${botId}/sources/${sourceId}`, { method: 'DELETE' }),
  getConversations: (botId) => apiFetch(`/api/bots/${botId}/conversations`),
  chat: (botId, data) => apiFetch(`/api/chat/${botId}`, { method: 'POST', body: JSON.stringify(data) }),
};

export function isLoggedIn() { return !!localStorage.getItem('brochat_token'); }
export function logout() { localStorage.removeItem('brochat_token'); window.location.href = '/'; }
