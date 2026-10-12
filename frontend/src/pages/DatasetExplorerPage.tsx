import { useEffect, useState } from "react";
import { api } from "../services/api";
import { EmptyState } from "../components/EmptyState";

export function DatasetExplorerPage() {
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [selected, setSelected] = useState<string>("catalog");
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.datasets().then((d) => setRows(d.datasets)).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    setError(null);
    api
      .dataset(selected)
      .then(setDetail)
      .catch((e) => {
        setDetail(null);
        setError(e.message);
      });
  }, [selected]);

  return (
    <div className="space-y-6">
      <h1 className="font-display text-3xl">Dataset explorer</h1>
      <p className="text-sm text-ink-500">Read-only views of the original catalogue, simulated events, and ML training table. Application checkout orders live in SQLite, not these CSVs.</p>
      <div className="flex flex-wrap gap-2">
        {["catalog", "events", "training"].map((id) => (
          <button
            key={id}
            onClick={() => setSelected(id)}
            className={`rounded-full border px-3 py-1 text-sm ${selected === id ? "border-brand-500 bg-brand-50" : ""}`}
          >
            {id}
          </button>
        ))}
      </div>
      {error && <EmptyState title="Dataset unavailable" body={error} />}
      {detail && (
        <div className="space-y-4">
          <div className="rounded-2xl border bg-white p-4 text-sm">
            <p className="font-semibold">{String(detail.kind)}</p>
            <p className="text-ink-500">{String(detail.description)}</p>
            <p className="mt-2">Rows: {String(detail.rows)}</p>
            {"unique_orders" in detail && <p>Unique orders: {String(detail.unique_orders)}</p>}
            {"target_rate" in detail && <p>partner_found rate: {Number(detail.target_rate).toFixed(3)}</p>}
            {"t_min" in detail && (
              <p>
                t range: {String(detail.t_min)} – {String(detail.t_max)} (simulated minutes)
              </p>
            )}
          </div>
          <div className="overflow-x-auto rounded-2xl border bg-white">
            <table className="w-full text-left text-xs">
              <thead>
                <tr>
                  {((detail.columns as Array<{ name: string }>) || []).map((c) => (
                    <th key={c.name} className="p-2">
                      {c.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {((detail.sample as Array<Record<string, unknown>>) || []).map((r, i) => (
                  <tr key={i} className="border-t">
                    {((detail.columns as Array<{ name: string }>) || []).map((c) => (
                      <td key={c.name} className="p-2">
                        {String(r[c.name] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {rows.some((r) => r.missing) && (
        <p className="text-sm">Some files are missing on disk. Generate them with scripts\generate_artefacts.py.</p>
      )}
    </div>
  );
}
