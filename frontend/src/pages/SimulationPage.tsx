import { useCallback, useState } from "react";
import { api } from "../services/api";
import { usePoll } from "../hooks/usePoll";
import { StatusBadge } from "../components/StatusBadge";
import type { SimStatus } from "../types";

export function SimulationPage() {
  const fn = useCallback(() => api.simStatus(), []);
  const { data, error } = usePoll<SimStatus>(fn, 800);
  const [msg, setMsg] = useState<string | null>(null);

  const run = async (fnx: () => Promise<unknown>) => {
    try {
      await fnx();
      setMsg(null);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Failed");
    }
  };

  if (error) return <p className="text-red-700">{error}</p>;
  if (!data) return <p>Loading simulation…</p>;

  return (
    <div className="space-y-6">
      <h1 className="font-display text-3xl">Live simulation</h1>
      <p className="text-sm text-ink-500">{data.simulation_label}</p>
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge value={data.status} />
        <button className="rounded-lg bg-brand-500 px-3 py-2 text-sm text-white" onClick={() => run(() => api.simStart())}>
          Start
        </button>
        <button className="rounded-lg border px-3 py-2 text-sm" onClick={() => run(() => api.simPause())}>
          Pause
        </button>
        <button className="rounded-lg border px-3 py-2 text-sm" onClick={() => run(() => api.simResume())}>
          Resume
        </button>
        <button className="rounded-lg border px-3 py-2 text-sm" onClick={() => run(() => api.simReset())}>
          Reset
        </button>
        <button className="rounded-lg bg-ink-900 px-3 py-2 text-sm text-white" onClick={() => run(() => api.simStep(1))}>
          Next event
        </button>
        <button className="rounded-lg border px-3 py-2 text-sm" onClick={() => run(() => api.simStep(10))}>
          +10 events
        </button>
      </div>
      <label className="block max-w-sm text-sm">
        Playback speed (sim minutes per real second)
        <input
          type="range"
          min={1}
          max={120}
          value={data.speed}
          onChange={(e) => api.simSpeed(Number(e.target.value))}
          className="w-full"
        />
        <span className="text-ink-500">{data.speed}×</span>
      </label>
      {msg && <p className="text-sm text-red-700">{msg}</p>}
      <dl className="grid gap-3 sm:grid-cols-3">
        {[
          ["Simulated time t", data.clock.toFixed(2)],
          ["Event index", `${data.event_index} / ${data.total_events}`],
          ["Active orders", data.active_orders],
          ["Waiting", data.waiting_orders],
          ["Pooled (decision)", data.pooled_orders],
          ["Customer queue", data.customer_queued],
        ].map(([k, v]) => (
          <div key={String(k)} className="rounded-2xl border border-stone-200 bg-white p-4">
            <dt className="text-xs uppercase text-ink-500">{k}</dt>
            <dd className="font-display text-2xl">{v}</dd>
          </div>
        ))}
      </dl>
      {data.total_events === 0 && (
        <p className="rounded-xl bg-amber-50 p-3 text-sm">
          No event file loaded. From the project root run:{" "}
          <code>.\.venv\Scripts\python.exe scripts\generate_artefacts.py</code>
        </p>
      )}
    </div>
  );
}
