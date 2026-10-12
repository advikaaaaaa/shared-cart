export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-stone-300 bg-white px-6 py-12 text-center">
      <p className="font-display text-lg text-ink-900">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-ink-500">{body}</p>
    </div>
  );
}
