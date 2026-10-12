export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-500 text-sm font-bold text-white">
        SC
      </span>
      <span>
        <span className="block font-display text-lg font-semibold leading-none text-ink-900">SharedCart</span>
        {!compact && (
          <span className="mt-0.5 hidden text-[11px] text-ink-500 sm:block">Intelligent order pooling</span>
        )}
      </span>
    </div>
  );
}
