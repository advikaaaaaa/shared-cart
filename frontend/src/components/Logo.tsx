import { ShoppingBasket } from "lucide-react";

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-lime-300 text-emerald-950">
        <ShoppingBasket className="h-5 w-5" />
      </span>
      <span>
        <span className="block font-display text-lg font-semibold leading-none text-[#183c30]">SharedCart</span>
        {!compact && (
          <span className="mt-0.5 hidden text-[11px] text-ink-500 sm:block">Saath mein, smarter delivery</span>
        )}
      </span>
    </div>
  );
}
