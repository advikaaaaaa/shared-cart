const BASE = "";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      detail = await res.text();
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<{ ok: boolean; model_loaded: boolean; model_error: string | null; model_name?: string }>("/api/health"),
  catalog: (q?: string, category?: string) =>
    req<{ disclaimer: string; categories: string[]; zones: import("../types").Zone[]; count: number; items: import("../types").CatalogItem[] }>(
      `/api/catalog?limit=240${q ? `&q=${encodeURIComponent(q)}` : ""}${category && category !== "all" ? `&category=${encodeURIComponent(category)}` : ""}`,
    ),
  simStatus: () => req<import("../types").SimStatus>("/api/simulation/status"),
  simStart: () => req("/api/simulation/start", { method: "POST" }),
  simPause: () => req("/api/simulation/pause", { method: "POST" }),
  simResume: () => req("/api/simulation/resume", { method: "POST" }),
  simReset: () => req("/api/simulation/reset", { method: "POST" }),
  simStep: (n = 1) => req(`/api/simulation/step?n=${n}`, { method: "POST" }),
  simSpeed: (speed: number) => req("/api/simulation/speed", { method: "POST", body: JSON.stringify({ speed }) }),
  orders: (params?: { source?: string; status?: string; q?: string }) => {
    const qs = new URLSearchParams();
    if (params?.source) qs.set("source", params.source);
    if (params?.status) qs.set("status", params.status);
    if (params?.q) qs.set("q", params.q);
    const s = qs.toString();
    return req<{ orders: import("../types").Order[] }>(`/api/orders${s ? `?${s}` : ""}`);
  },
  placeOrder: (body: { cell: number; customer_name: string; items: { item_id: string; item_type?: string; unit_price: number; quantity: number }[] }) =>
    req<{ order: import("../types").Order; message: string }>("/api/orders", { method: "POST", body: JSON.stringify(body) }),
  order: (id: number) => req<{ order: import("../types").Order }>(`/api/orders/${id}`),
  tracking: (id: number) => req<import("../types").Tracking>(`/api/orders/${id}/tracking`),
  predict: (order_id: number, wait_minutes: number, radius_m: number) =>
    req<Record<string, unknown>>("/api/predictions", {
      method: "POST",
      body: JSON.stringify({ order_id, wait_minutes, radius_m }),
    }),
  dashboard: () => req<Record<string, unknown>>("/api/ops/dashboard"),
  metrics: () => req<Record<string, unknown>>("/api/models/metrics"),
  impact: () => req<Record<string, unknown>>("/api/analytics/impact"),
  impactRecompute: (body: { fee: number; lam: number; detour: number }) =>
    req<Record<string, unknown>>("/api/analytics/impact", { method: "POST", body: JSON.stringify(body) }),
  datasets: () => req<{ datasets: Record<string, unknown>[] }>("/api/datasets/summary"),
  dataset: (name: string) => req<Record<string, unknown>>(`/api/datasets/${name}`),
};
