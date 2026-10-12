import { useCallback, useState } from "react";
import { api } from "../services/api";
import { usePoll } from "../hooks/usePoll";
import { StatusBadge } from "../components/StatusBadge";
import type { Order } from "../types";

export function PoolingSimulatorPage() {
  const [oid, setOid] = useState<number | "">("");
  const [wait, setWait] = useState(8);
  const [radius, setRadius] = useState(600);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadOrders = useCallback(() => api.orders(), []);
  const { data: orderData } = usePoll(loadOrders, 2000);
  const orders = (orderData?.orders || []).filter((o: Order) => o.small);
  const oidValid = typeof oid === "number" && orders.some((o) => o.order_id === oid);
  const selectedId = oidValid ? oid : orders[0]?.order_id;

  const run = async () => {
    if (selectedId == null) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.predict(Number(selectedId), wait, radius));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Prediction failed");
      setResult(null);
    } finally {
      setBusy(false);
    }
  };

  const pred = result?.prediction as { probability?: number; predicted_class?: number; predicted_label?: string } | undefined;
  const decision = result?.decision as { action?: string; reason?: string; compatibility?: unknown[] } | undefined;
  const cands = (result?.observed_candidates as unknown[]) || [];

  return (
    <div className="space-y-6">
      <h1 className="font-display text-3xl">Pooling Simulator</h1>
      <p className="text-sm text-ink-500">
        Probability is a forecast of partner_found. Candidates are only orders already played. The decision engine
        combines both — a high probability is not a confirmed pool.
      </p>
      <div className="grid gap-3 rounded-2xl border border-stone-200 bg-white p-4 md:grid-cols-4">
        <label className="text-sm">
          Eligible order
          <select className="mt-1 w-full rounded-lg border px-2 py-2" value={selectedId ?? ""} onChange={(e) => setOid(Number(e.target.value))}>
            {orders.length === 0 && <option value="">No active small orders — step the simulation</option>}
            {orders.map((o) => (
              <option key={o.order_id} value={o.order_id}>
                #{o.order_id} · ₹{o.value} · cell {o.cell}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Wait (min)
          <select className="mt-1 w-full rounded-lg border px-2 py-2" value={wait} onChange={(e) => setWait(Number(e.target.value))}>
            {[2, 5, 8, 10, 15].map((w) => (
              <option key={w}>{w}</option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Radius (m)
          <select className="mt-1 w-full rounded-lg border px-2 py-2" value={radius} onChange={(e) => setRadius(Number(e.target.value))}>
            {[300, 600, 900].map((w) => (
              <option key={w}>{w}</option>
            ))}
          </select>
        </label>
        <button disabled={busy || selectedId == null} onClick={run} className="self-end rounded-xl bg-brand-500 py-2 font-semibold text-white">
          {busy ? "Running…" : "Run prediction"}
        </button>
      </div>
      {error && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      {result && pred && (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border bg-white p-5">
            <p className="text-xs uppercase text-ink-500">Predicted partner-found probability</p>
            <p className="font-display text-5xl text-brand-600">{((pred.probability || 0) * 100).toFixed(1)}%</p>
            <div className="mt-3 h-2 rounded-full bg-stone-100">
              <div className="h-2 rounded-full bg-brand-500" style={{ width: `${(pred.probability || 0) * 100}%` }} />
            </div>
            <p className="mt-2 text-sm">
              Class: {pred.predicted_label} ({pred.predicted_class}) · wait {wait} min · radius {radius} m
            </p>
          </div>
          <div className="rounded-2xl border bg-white p-5">
            <p className="text-xs uppercase text-ink-500">Recommended action</p>
            <p className="mt-1">
              <StatusBadge value={decision?.action} />
            </p>
            <p className="mt-3 text-sm text-ink-700">{decision?.reason}</p>
            <p className="mt-3 text-xs text-ink-500">{String(result.disclaimer || "")}</p>
          </div>
          <div className="rounded-2xl border bg-white p-5 lg:col-span-2">
            <h2 className="text-sm font-semibold">Observed candidates ({cands.length})</h2>
            {cands.length === 0 ? (
              <p className="mt-2 text-sm text-ink-500">None in the played stream for this wait/radius.</p>
            ) : (
              <pre className="mt-2 overflow-auto text-xs">{JSON.stringify(cands, null, 2)}</pre>
            )}
            <h2 className="mt-4 text-sm font-semibold">Compatibility</h2>
            <pre className="mt-2 overflow-auto text-xs">{JSON.stringify(decision?.compatibility || [], null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
