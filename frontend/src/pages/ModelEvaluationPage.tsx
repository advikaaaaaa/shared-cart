import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../services/api";

export function ModelEvaluationPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.metrics().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-700">{error}</p>;
  if (!data) return <p>Loading metrics…</p>;

  const comparison = (data.comparison as Array<Record<string, unknown>>) || [];
  const confusion = (data.confusion as Array<Record<string, unknown>>) || [];
  const calibration = (data.calibration as Array<Record<string, unknown>>) || [];
  const importance = (data.importance as Array<Record<string, unknown>>) || [];
  const zone = (data.zone_auc as Array<Record<string, unknown>>) || [];
  const meta = (data.meta as Record<string, unknown>) || {};

  return (
    <div className="space-y-6">
      <h1 className="font-display text-3xl">Model evaluation</h1>
      <p className="rounded-xl bg-amber-50 p-3 text-sm">{String(data.disclaimer)}</p>
      <p className="text-sm text-ink-700">
        Best saved pipeline: <strong>{String(meta.best_model || "not trained yet")}</strong> · test ROC-AUC{" "}
        {meta.test_roc_auc != null ? Number(meta.test_roc_auc).toFixed(4) : "—"}. Hyperparameters were fixed in the
        notebook; the test split was not used for repeated tuning.
      </p>
      {comparison.length === 0 && <p className="text-sm">No comparison CSV yet. Run scripts\generate_artefacts.py</p>}
      <div className="overflow-x-auto rounded-2xl border bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-stone-50 text-xs uppercase text-ink-500">
            <tr>
              {["Model", "Features", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC", "Brier"].map((h) => (
                <th key={h} className="p-3">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {comparison.map((r, i) => (
              <tr key={i} className="border-t">
                <td className="p-3">{String(r.Model)}</td>
                <td>{String(r.Features)}</td>
                <td>{r.Accuracy as number}</td>
                <td>{r.Precision as number}</td>
                <td>{r.Recall as number}</td>
                <td>{r.F1 as number}</td>
                <td>{r["ROC-AUC"] as number}</td>
                <td>{r.Brier as number}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border bg-white p-4">
          <h2 className="mb-2 text-sm font-semibold">Test ROC-AUC by model (final features)</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={comparison.filter((r) => String(r.Features).includes("Final"))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="Model" hide />
              <YAxis domain={[0.5, 1]} />
              <Tooltip />
              <Bar dataKey="ROC-AUC" fill="#e25b2c" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="rounded-2xl border bg-white p-4">
          <h2 className="mb-2 text-sm font-semibold">Calibration</h2>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={calibration}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="pred_mean" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="frac_positive" stroke="#e25b2c" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="overflow-x-auto rounded-2xl border bg-white">
        <h2 className="p-3 text-sm font-semibold">Confusion matrices (threshold 0.5)</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-ink-500">
              <th className="p-3">Model</th>
              <th>Features</th>
              <th>TN</th>
              <th>FP</th>
              <th>FN</th>
              <th>TP</th>
            </tr>
          </thead>
          <tbody>
            {confusion.map((r, i) => (
              <tr key={i} className="border-t">
                <td className="p-3">{String(r.Model)}</td>
                <td>{String(r.Features)}</td>
                <td>{String(r.tn)}</td>
                <td>{String(r.fp)}</td>
                <td>{String(r.fn)}</td>
                <td>{String(r.tp)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {importance.length > 0 && (
        <div className="rounded-2xl border bg-white p-4">
          <h2 className="mb-2 text-sm font-semibold">Permutation importance (AUC drop)</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={importance.slice(0, 12)} layout="vertical">
              <XAxis type="number" />
              <YAxis type="category" dataKey="feature" width={160} />
              <Tooltip />
              <Bar dataKey="auc_drop" fill="#c94a1f" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      {zone.length > 0 && (
        <p className="text-sm">
          Zone AUC: {zone.map((z) => `${z.zone_type ?? Object.values(z)[0]}`).join(" · ")} (see CSV for values)
        </p>
      )}
    </div>
  );
}
