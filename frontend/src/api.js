const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, { method = "GET", body } = {}) {
  const response = await fetch(BASE + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
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
