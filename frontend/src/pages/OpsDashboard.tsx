import { useCallback, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../services/api";
import { usePoll } from "../hooks/usePoll";
import { MetricCard } from "../components/MetricCard";
import { StatusBadge } from "../components/StatusBadge";
import { EmptyState } from "../components/EmptyState";

type Dash = {
  status: { status: string; clock: number; event_index: number; total_events: number };
  metrics: Record<string, number>;
  by_status: Record<string, number>;
  by_zone: Record<string, number>;
  recent: Array<Record<string, unknown>>;
  timeline: Array<{ order_id: number; status: string; sim_t: number; note: string }>;
};

export function OpsDashboard() {
  const fn = useCallback(() => api.dashboard() as Promise<Dash>, []);
  const { data, error } = usePoll<Dash>(fn, 1500);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");

  const filtered = useMemo(() => {
    let rows = (data?.recent || []) as Array<Record<string, unknown>>;
    if (q) rows = rows.filter((r) => String(r.order_id).includes(q));
    if (status) rows = rows.filter((r) => r.status === status);
    return rows;
  }, [data, q, status]);

  if (error) return <p className="text-red-700">{error}</p>;
  if (!data) return <p>Loading dashboard…</p>;
  const m = data.metrics || {};
  const empty = (m.introduced || 0) === 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl">Operations</h1>
          <p className="text-sm text-ink-500">Live figures from the event player — not hardcoded.</p>
        </div>
        <StatusBadge value={data.status.status} />
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Orders introduced" value={m.introduced ?? 0} />
        <MetricCard label="Active" value={m.active ?? 0} />
        <MetricCard label="Waiting" value={m.waiting ?? 0} />
        <MetricCard label="Pooled" value={m.pooled ?? 0} />
        <MetricCard label="Dispatched independently" value={m.dispatched_independent ?? 0} />
        <MetricCard label="Pooling rate" value={`${((m.pooling_rate || 0) * 100).toFixed(1)}%`} />
        <MetricCard label="Avg wait (sim min)" value={(m.avg_wait || 0).toFixed(2)} />
        <MetricCard label="Est. savings (₹ sim)" value={(m.estimated_savings || 0).toFixed(0)} hint="Notebook fee formula" />
      </div>
      {empty && (
        <EmptyState
          title="No events processed yet"
          body="Open Simulation and use Next event (or Start) to replay the dataset. Metrics will fill in from actual decisions."
        />
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-stone-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-semibold">Status distribution</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={Object.entries(data.by_status || {}).map(([name, n]) => ({ name, n }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="n" fill="#e25b2c" radius={4} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="rounded-2xl border border-stone-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-semibold">Zone demand (played orders)</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={Object.entries(data.by_zone || {}).map(([name, n]) => ({ name, n }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" hide />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="n" fill="#c94a1f" radius={4} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="flex gap-2">
        <input className="rounded-xl border px-3 py-2 text-sm" placeholder="Search order ID" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="rounded-xl border px-3 py-2 text-sm" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {Object.keys(data.by_status || {}).map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </div>
      <div className="overflow-x-auto rounded-2xl border border-stone-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-stone-50 text-xs uppercase text-ink-500">
            <tr>
              <th className="p-3">Order</th>
              <th>Status</th>
              <th>Decision</th>
              <th>Value</th>
              <th>Cell</th>
              <th>P(partner)</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <tr key={String(r.order_id)} className="border-t">
                <td className="p-3">{String(r.order_id)}</td>
                <td>
                  <StatusBadge value={String(r.status)} />
                </td>
                <td>
                  <StatusBadge value={r.decision ? String(r.decision) : null} />
                </td>
                <td>₹{String(r.value)}</td>
                <td>{String(r.cell)}</td>
                <td>{r.probability != null ? Number(r.probability).toFixed(3) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="rounded-2xl border border-stone-200 bg-white p-4">
        <h2 className="mb-2 text-sm font-semibold">Recent event timeline</h2>
        <ul className="max-h-64 space-y-2 overflow-auto text-sm">
          {(data.timeline || []).slice().reverse().map((h, i) => (
            <li key={i} className="border-b border-stone-100 pb-2">
              <span className="font-medium">#{h.order_id}</span> · {h.status} @ t={h.sim_t?.toFixed?.(2) ?? h.sim_t} — {h.note}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
