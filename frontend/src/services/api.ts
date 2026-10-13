const BASE = "";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const payload = await res.text();
    let detail: unknown = payload || res.statusText;
    try {
      const body = JSON.parse(payload) as { detail?: unknown };
      detail = body.detail ?? body;
    } catch {
      detail = payload || res.statusText;
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<{ ok: boolean; model_loaded: boolean; model_error: string | null; model_name?: string }>("/api/health"),
  catalog: (q?: string, category?: string, page = 1) =>
    req<{ disclaimer: string; categories: string[]; zones: import("../types").Zone[]; count: number; page: number; page_size: number; items: import("../types").CatalogItem[] }>(
      `/api/catalog?limit=12&page=${page}${q ? `&q=${encodeURIComponent(q)}` : ""}${category && category !== "all" ? `&category=${encodeURIComponent(category)}` : ""}`,
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
  placeOrder: (body: { customer_name: string; items: { item_id: string; item_type?: string; unit_price: number; quantity: number }[] }) =>
    req<{ order: import("../types").Order; access_key: string; message: string }>("/api/orders", { method: "POST", body: JSON.stringify(body) }),
  order: (id: number) => req<{ order: import("../types").Order }>(`/api/orders/${id}`, { headers: orderHeaders(id) }),
  tracking: (id: number) => req<import("../types").Tracking>(`/api/orders/${id}/tracking`, { headers: orderHeaders(id) }),
  poolingEstimate: (body: { value: number; n_items: number }) =>
    req<{
      recommended_wait_minutes: number;
      best_window_wait_minutes: number;
      best_window_radius_m: number | null;
      radius_m: number | null;
      partner_probability: number | null;
      recent_small_orders_600m: number;
      recent_small_orders_900m: number;
      model_name: string;
      forecast_hour: number;
      daypart: string;
      historical_demand_index: number;
      historical_demand_change_percent: number | null;
      disclaimer: string;
    }>("/api/pooling/estimate", { method: "POST", body: JSON.stringify(body) }),
  saveOrderAccessKey: (id: number, key: string) => sessionStorage.setItem(`sharedcart-order-key-${id}`, key),
  adminSession: () => req<{ authenticated: boolean }>("/api/admin/session"),
  adminLogin: (username: string, password: string) =>
    req<{ authenticated: boolean }>("/api/admin/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  adminLogout: () => req<{ authenticated: boolean }>("/api/admin/logout", { method: "POST" }),
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

function orderHeaders(id: number): HeadersInit {
  const key = sessionStorage.getItem(`sharedcart-order-key-${id}`);
  return key ? { "X-Order-Access-Key": key } : {};
}
