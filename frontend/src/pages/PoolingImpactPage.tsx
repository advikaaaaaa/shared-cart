import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../services/api";

export function PoolingImpactPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [fee, setFee] = useState(40);
  const [lam, setLam] = useState(2);
  const [detour, setDetour] = useState(2);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => api.impact().then(setData).catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  const recompute = async () => {
    setBusy(true);
    setError(null);
    try {
      setData(await api.impactRecompute({ fee, lam, detour }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Recompute failed");
    } finally {
      setBusy(false);
    }
  };

  const assumptions = (data?.assumptions as Record<string, unknown>) || {};
  const offline = (data?.offline_test_policies as Array<Record<string, unknown>>) || [];
  const live = (data?.live_simulation as Record<string, unknown>) || {};

  return (
    <div className="space-y-6">
      <h1 className="font-display text-3xl">Pooling impact</h1>
      <p className="text-sm text-ink-700">
        Offline columns reuse the notebook policy evaluation on held-out test orders. Live columns come from the event
        player. All rupee figures are simulated using the stated fee and delay-cost assumptions — not commercial savings.
      </p>
      <div className="rounded-2xl border bg-white p-4 text-sm">
        <p className="font-semibold">Cost assumptions</p>
        <p className="mt-1 text-ink-500">{String(assumptions.note || "")}</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <label>
            Delivery fee ₹
            <input type="number" className="mt-1 w-full rounded-lg border px-2 py-1" value={fee} onChange={(e) => setFee(Number(e.target.value))} />
          </label>
          <label>
            λ ₹ / delay-minute
            <input type="number" className="mt-1 w-full rounded-lg border px-2 py-1" value={lam} onChange={(e) => setLam(Number(e.target.value))} />
          </label>
          <label>
            Detour min / grid cell
            <input type="number" className="mt-1 w-full rounded-lg border px-2 py-1" value={detour} onChange={(e) => setDetour(Number(e.target.value))} />
          </label>
        </div>
        <button disabled={busy} onClick={recompute} className="mt-3 rounded-xl bg-brand-500 px-4 py-2 text-white">
          {busy ? "Recomputing…" : "Recompute offline policies"}
        </button>
      </div>
      {error && <p className="text-red-700">{error}</p>}
      {offline.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-2xl border bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-stone-50 text-xs uppercase text-ink-500">
                <tr>
                  {Object.keys(offline[0]).map((k) => (
                    <th key={k} className="p-3">
                      {k}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {offline.map((r, i) => (
                  <tr key={i} className="border-t">
                    {Object.values(r).map((v, j) => (
                      <td key={j} className="p-3">
                        {String(v)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="rounded-2xl border bg-white p-4">
            <h2 className="mb-2 text-sm font-semibold">Net (₹ simulated) by policy</h2>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={offline}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="Policy" hide />
                <YAxis />
                <Tooltip />
                <Bar dataKey="net" fill="#e25b2c" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
      <div className="rounded-2xl border bg-white p-4">
        <h2 className="font-semibold">Live simulation (played events)</h2>
        <dl className="mt-3 grid gap-3 sm:grid-cols-3 text-sm">
          {Object.entries(live)
            .filter(([k]) => k !== "note")
            .map(([k, v]) => (
              <div key={k}>
                <dt className="text-ink-500">{k}</dt>
                <dd>{typeof v === "number" ? v.toFixed(3) : String(v)}</dd>
              </div>
            ))}
        </dl>
        <p className="mt-3 text-xs text-ink-500">{String(live.note || "")}</p>
      </div>
    </div>
  );
}
