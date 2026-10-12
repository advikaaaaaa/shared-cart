import { Link } from "react-router-dom";
import { useCart } from "../hooks/useCart";
import { EmptyState } from "../components/EmptyState";

export function CartPage() {
  const cart = useCart();
  if (cart.lines.length === 0) {
    return <EmptyState title="Your cart is empty" body="Browse the sample grocery catalogue and add items to place a simulated order." />;
  }
  return (
    <div className="grid gap-8 md:grid-cols-[1fr_280px]">
      <div className="space-y-3">
        {cart.lines.map((l) => (
          <div key={l.item_id} className="flex items-center justify-between rounded-2xl border border-stone-200 bg-white p-4">
            <div>
              <p className="font-medium">{l.item_type}</p>
              <p className="text-xs text-ink-500">
                {l.item_id} · ₹{l.item_price}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button className="h-8 w-8 rounded-lg border" onClick={() => cart.dec(l.item_id)}>
                −
              </button>
              <span className="w-6 text-center">{l.quantity}</span>
              <button className="h-8 w-8 rounded-lg border" onClick={() => cart.inc(l.item_id)}>
                +
              </button>
              <button className="ml-2 text-xs text-red-700" onClick={() => cart.remove(l.item_id)}>
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>
      <aside className="h-fit rounded-2xl border border-stone-200 bg-white p-5">
        <p className="text-sm text-ink-500">Subtotal</p>
        <p className="font-display text-3xl">₹{cart.subtotal}</p>
        <p className="mt-2 text-xs text-ink-500">Simulated checkout — no payment is collected. Delivery fee logic is applied in operations.</p>
        <Link
          to="/checkout"
          className="mt-4 block rounded-xl bg-brand-500 py-2.5 text-center text-sm font-semibold text-white"
        >
          Continue to checkout
        </Link>
      </aside>
    </div>
  );
}
