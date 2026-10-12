import { useCallback } from "react";
import { useParams } from "react-router-dom";
import { api } from "../services/api";
import { usePoll } from "../hooks/usePoll";
import { StatusBadge } from "../components/StatusBadge";
import type { Tracking } from "../types";

export function TrackingPage() {
  const { id } = useParams();
  const fn = useCallback(() => api.tracking(Number(id)), [id]);
  const { data, error } = usePoll<Tracking>(fn, 1500);

  if (error) return <p className="text-red-700">{error}</p>;
  if (!data) return <p>Loading tracking…</p>;
  const { order, stages, clock } = data;

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <p className="text-xs uppercase text-ink-500">Order {order.order_id}</p>
        <h1 className="font-display text-3xl">Tracking</h1>
        <p className="mt-1 text-sm text-ink-500">
          Simulation clock: {clock.toFixed(2)} min · <StatusBadge value={order.status} />
        </p>
      </div>
      <ol className="space-y-3">
        {stages.map((s) => (
          <li key={s.key} className={`rounded-xl border p-3 ${s.done ? "border-brand-200 bg-white" : "border-stone-200 bg-stone-50 text-ink-500"}`}>
            <span className="text-sm font-medium">{s.label}</span>
            {s.key === "pooled" && !s.done && (
              <p className="mt-1 text-xs">Pooling is confirmed only after a real simulated candidate passes checks — not from probability alone.</p>
            )}
          </li>
        ))}
      </ol>
      {order.decision === "DISPATCH" && order.partner_order_id == null && (
        <p className="rounded-xl bg-sky-50 p-3 text-sm">This order was dispatched without pooling.</p>
      )}
      {order.reason && <p className="text-sm text-ink-700">{order.reason}</p>}
    </div>
  );
}
