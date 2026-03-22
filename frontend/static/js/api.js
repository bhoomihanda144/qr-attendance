/**
 * api.js — Centralised fetch wrapper
 * All backend calls go through these helpers.
 */

const API_BASE = '/api';

/**
 * Generic JSON request.
 * Returns parsed JSON or throws an error object.
 */
async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw data;
  return data;
}

// Shorthand helpers
const API = {
  get:    (path)         => apiFetch(path),
  post:   (path, body)   => apiFetch(path, { method: 'POST',   body: JSON.stringify(body) }),
  delete: (path)         => apiFetch(path, { method: 'DELETE' }),

  // Auth
  teacherLogin:    (body) => API.post('/auth/teacher/login', body),
  teacherRegister: (body) => API.post('/auth/teacher/register', body),
  studentLogin:    (body) => API.post('/auth/student/login', body),
  studentRegister: (body) => API.post('/auth/student/register', body),
  logout:          ()     => API.post('/auth/logout'),
  me:              ()     => API.get('/auth/me'),

  // Sessions
  createSession:   (body)      => API.post('/sessions/create', body),
  mySessions:      ()          => API.get('/sessions/my'),
  allSessions:     ()          => API.get('/sessions/all'),
  deleteSession:   (id)        => API.delete(`/sessions/${id}`),
  sessionAttendance: (id)      => API.get(`/sessions/${id}/attendance`),

  // Attendance
  markAttendance:  (payload)   => API.post('/attendance/mark', { qr_payload: payload }),
  myAttendance:    (subject)   => API.get(`/attendance/my${subject ? `?subject=${encodeURIComponent(subject)}` : ''}`),
  allAttendance:   (sub, date) => {
    const params = new URLSearchParams();
    if (sub)  params.set('subject', sub);
    if (date) params.set('date', date);
    return API.get(`/attendance/all?${params}`);
  },
  subjects:        ()          => API.get('/attendance/subjects'),

  // Analytics
  dashboard:       ()   => API.get('/analytics/dashboard'),
  studentAnalytics:()   => API.get('/analytics/students'),
  predictions:     ()   => API.get('/analytics/predict'),
  anomalies:       ()   => API.get('/analytics/anomalies'),
  myStats:         ()   => API.get('/analytics/my-stats'),
};
