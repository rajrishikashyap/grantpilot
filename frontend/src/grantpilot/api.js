// API client for the GrantPilot backend.
//
// One place that knows the backend URL and how to call it. The base URL comes
// from VITE_API_URL if set (for the deployed build), else localhost:8000 for
// local dev. Every call posts JSON and throws a readable Error on failure, so
// the UI can show the message (e.g. the 503 when Ollama is not running).

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function post(path, body) {
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `${path} failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  eligibility: (b) => post("/eligibility", b),
  budget: (b) => post("/budget", b),
  risk: (b) => post("/risk", b),
  search: (b) => post("/search", b),
  assess: (b) => post("/assess", b),
  health: async () => (await fetch(BASE + "/health")).json(),
};
