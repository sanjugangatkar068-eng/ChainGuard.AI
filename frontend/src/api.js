const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
// Optional: sent as X-API-Key when the backend has API_KEY configured.
const API_KEY = import.meta.env.VITE_API_KEY || "";

async function request(path, { method = "GET", body } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (API_KEY) headers["X-API-Key"] = API_KEY;

  const response = await fetch(BASE + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data?.detail;
    throw new Error(
      typeof detail === "string" ? detail : detail ? "Request failed" : response.statusText
    );
  }
  return data;
}

export const api = {
  dashboard: () => request("/api/dashboard"),
  signals: (limit = 8) => request(`/api/signals?limit=${limit}`),
  orchestrator: () => request("/api/orchestrator"),
  runCycle: (limit = 5) =>
    request(`/api/orchestrator/cycle?limit=${limit}`, { method: "POST" }),
  createDisruption: (body) => request("/api/disruptions", { method: "POST", body }),
  analyze: (body) => request("/api/analyze", { method: "POST", body }),
  approvals: (limit = 10) => request(`/api/approvals?limit=${limit}`),
  decide: (id, body) =>
    request(`/api/approvals/${id}/decision`, { method: "POST", body }),
  alerts: (limit = 10) => request(`/api/alerts?limit=${limit}`),
  ackAlert: (id) => request(`/api/alerts/${id}/ack`, { method: "POST" }),
  audit: (limit = 12) => request(`/api/audit?limit=${limit}`),
};

export const API_BASE = BASE;
