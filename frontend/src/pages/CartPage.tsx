import { ArrowRight, Minus, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/EmptyState";
import { useCart } from "../hooks/useCart";

export function CartPage() {
  const cart = useCart();
  if (cart.lines.length === 0) {
    return (
      <div className="mx-auto max-w-xl rounded-3xl border border-stone-200 bg-white p-8 text-center">
        <EmptyState title="Your bag is taking a breather" body="Browse the grocery picks and add the little things you need." />
        <Link to="/" className="mt-4 inline-flex rounded-full bg-[#183c30] px-5 py-3 text-sm font-semibold text-white">Browse groceries</Link>
      </div>
    );
  }
  return (
    <div className="grid gap-7 lg:grid-cols-[1fr_350px]">
      <section>
        <p className="text-xs font-bold uppercase tracking-[.16em] text-brand-600">Your picks</p>
        <div className="mt-1 flex items-end justify-between">
          <h1 className="font-display text-3xl">The good stuff.</h1>
          <span className="text-xs text-ink-500">{cart.count} items</span>
        </div>
        <div className="mt-5 space-y-3">
          {cart.lines.map((l) => (
            <div key={l.item_id} className="flex items-center justify-between gap-3 rounded-2xl border border-stone-200 bg-white p-4">
              <div>
                <p className="font-semibold">{l.item_type}</p>
                <p className="mt-1 text-xs text-ink-500">₹{l.item_price} each</p>
              </div>
              <div className="flex items-center gap-2">
                <button aria-label={`Remove one ${l.item_type}`} className="grid h-8 w-8 place-items-center rounded-full border border-stone-300 hover:bg-stone-100" onClick={() => cart.dec(l.item_id)}>
                  <Minus className="h-3.5 w-3.5" />
                </button>
                <span className="w-5 text-center text-sm font-semibold">{l.quantity}</span>
                <button aria-label={`Add one ${l.item_type}`} className="grid h-8 w-8 place-items-center rounded-full border border-stone-300 hover:bg-stone-100" onClick={() => cart.inc(l.item_id)}>
                  <Plus className="h-3.5 w-3.5" />
                </button>
                <button aria-label={`Remove ${l.item_type}`} className="ml-1 grid h-8 w-8 place-items-center rounded-full text-stone-400 hover:bg-red-50 hover:text-red-700" onClick={() => cart.remove(l.item_id)}>
                  <Trash2 className="h-4 w-4" />
                </button>
                <span className="w-14 text-right text-sm font-semibold">₹{l.item_price * l.quantity}</span>
              </div>
            </div>
          ))}
        </div>
        <Link to="/" className="mt-4 inline-block text-sm font-semibold text-emerald-800 hover:underline">← Keep browsing</Link>
      </section>
      <aside className="h-fit rounded-2xl border border-stone-200 bg-white p-5 lg:sticky lg:top-24">
        <h2 className="font-display text-xl">A little total</h2>
        <div className="mt-4 flex justify-between border-b border-stone-100 pb-4 text-sm">
          <span className="text-ink-500">Basket subtotal</span><strong>₹{cart.subtotal}</strong>
        </div>
        {cart.subtotal < 99 ? (
          <p className="mt-4 rounded-xl bg-orange-50 p-3 text-xs leading-relaxed text-orange-950">Example only—not charged: this concept shows ₹9 delivery under ₹99 if no group forms, or waived delivery in a group. No real delivery is arranged.</p>
        ) : (
          <p className="mt-4 rounded-xl bg-emerald-50 p-3 text-xs leading-relaxed text-emerald-950">Example only—not charged: this concept illustrates free delivery for baskets of ₹99 or more. No real delivery is arranged.</p>
        )}
        <p className="mt-3 flex items-start gap-2 text-xs leading-relaxed text-ink-500">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700" />
          Example platform fee: ₹18 alone, split between up to 3 orders if shared. Your basket is never shown to other customers; no fee is charged here.
        </p>
        <p className="mt-3 text-[11px] text-ink-500">Prototype estimate only. No payment will be collected.</p>
        <Link to="/checkout" className="mt-5 flex items-center justify-center gap-2 rounded-xl bg-brand-500 py-3 text-sm font-semibold text-white">
          Continue to checkout <ArrowRight className="h-4 w-4" />
        </Link>
      </aside>
    </div>
  );
}
