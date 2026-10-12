const styles: Record<string, string> = {
  placed: "bg-stone-100 text-stone-700",
  evaluating: "bg-amber-50 text-amber-800",
  waiting: "bg-orange-50 text-orange-800",
  pooled: "bg-emerald-50 text-emerald-800",
  dispatched: "bg-sky-50 text-sky-800",
  delivered: "bg-green-50 text-green-800",
  WAIT: "bg-orange-50 text-orange-800",
  POOL: "bg-emerald-50 text-emerald-800",
  DISPATCH: "bg-sky-50 text-sky-800",
  running: "bg-emerald-50 text-emerald-800",
  paused: "bg-amber-50 text-amber-800",
  idle: "bg-stone-100 text-stone-600",
};

export function StatusBadge({ value }: { value?: string | null }) {
  if (!value) return <span className="text-ink-500">—</span>;
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${styles[value] || "bg-stone-100 text-stone-700"}`}>
      {value}
    </span>
  );
}
