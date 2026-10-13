import { useEffect, useState } from "react";
import { ArrowRight, Clock3, ShieldCheck, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import { useCart } from "../hooks/useCart";

type PoolEstimate = Awaited<ReturnType<typeof api.poolingEstimate>>;

export function CheckoutPage() {
  const cart = useCart();
  const nav = useNavigate();
  const [estimate, setEstimate] = useState<PoolEstimate | null>(null);
  const [estimateError, setEstimateError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!cart.subtotal || !cart.count) return;
    let current = true;
    setEstimate(null);
    setEstimateError(null);
    api
      .poolingEstimate({ value: cart.subtotal, n_items: cart.count })
      .then((result) => { if (current) setEstimate(result); })
      .catch((e: Error) => { if (current) setEstimateError(e.message); });
    return () => { current = false; };
  }, [cart.count, cart.subtotal]);

  if (cart.lines.length === 0) {
    return (
      <div className="mx-auto max-w-xl rounded-3xl border border-stone-200 bg-white p-8 text-center">
        <h1 className="font-display text-2xl">Your bag is waiting</h1>
        <p className="mt-2 text-sm text-ink-500">Add a few essentials before heading to checkout.</p>
        <button onClick={() => nav("/")} className="mt-5 rounded-xl bg-brand-500 px-5 py-3 text-sm font-semibold text-white">
          Browse groceries
        </button>
      </div>
    );
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.placeOrder({
        customer_name: "Guest",
        items: cart.lines.map((l) => ({
          item_id: l.item_id,
          item_type: l.item_type,
          unit_price: l.item_price,
          quantity: l.quantity,
        })),
      });
      api.saveOrderAccessKey(res.order.order_id, res.access_key);
      cart.clear();
      nav(`/orders/${res.order.order_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setBusy(false);
    }
  };
  const poolingEligible = cart.subtotal < 149;

  return (
    <form onSubmit={submit} className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[1fr_360px]">
      <section className="space-y-5">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-600">One last thing</p>
          <h1 className="mt-1 font-display text-4xl">Make this a smarter trip.</h1>
          <p className="mt-2 text-sm text-ink-500">No address or area selection is needed. We check the order history for a rough idea of when a shared trip may form.</p>
        </div>

        <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
          <div className="flex items-center gap-2 text-sm font-bold text-emerald-950">
            <Sparkles className="h-4 w-4" /> When could a shared trip happen?
          </div>
          {estimate ? (
            <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2">
              {estimate.partner_probability == null ? (
                <p className="text-sm text-emerald-950">A match estimate is not available for this basket size. You can still continue normally.</p>
              ) : (
                <>
                  <p><span className="block font-display text-3xl">{Math.round(estimate.partner_probability * 100)}%</span><span className="text-xs text-emerald-900">estimated chance within up to {estimate.best_window_wait_minutes} min</span></p>
                  <p className="flex items-center gap-2 text-sm text-emerald-900">
                    <Clock3 className="h-4 w-4" />
                    {estimate.recommended_wait_minutes
                      ? `Suggested wait: up to ${estimate.recommended_wait_minutes} min`
                      : "Not enough signal to recommend waiting"}
                  </p>
                  <p className="w-full text-xs text-emerald-900">
                    The sample shows {estimate.daypart} demand {estimate.historical_demand_change_percent == null ? "with no reliable comparison" : `${Math.abs(estimate.historical_demand_change_percent)}% ${estimate.historical_demand_change_percent >= 0 ? "above" : "below"} a typical hour`}.
                  </p>
                </>
              )}
            </div>
          ) : estimateError ? (
            <p className="mt-3 text-sm text-emerald-950">Forecast unavailable right now. Your order can still be placed; no match is promised.</p>
          ) : (
            <p className="mt-3 text-sm text-emerald-950">Checking recent simulated demand for this area…</p>
          )}
          <p className="mt-3 text-xs leading-relaxed text-emerald-900">
            {estimate?.disclaimer ?? "A forecast uses the saved sample's order patterns. It is not a live nearby order or a guaranteed pool."}
          </p>
          <p className="mt-2 text-xs font-semibold text-emerald-950">Waiting is optional. You can place your order now; this estimate never holds it.</p>
        </section>

        <div className="flex items-start gap-3 rounded-2xl bg-stone-100 p-4 text-xs leading-relaxed text-ink-700">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700" />
          Other customers never see your basket, name, or area. This is a concept preview: no real delivery is arranged and no payment is collected.
        </div>
      </section>

      <aside className="h-fit rounded-2xl border border-stone-200 bg-white p-5">
        <h2 className="font-display text-xl">Order preview</h2>
        <div className="mt-4 space-y-3 border-b border-stone-100 pb-4 text-sm">
          <div className="flex justify-between"><span className="text-ink-500">Groceries</span><span>₹{cart.subtotal}</span></div>
          <div className="flex justify-between"><span className="text-ink-500">Example delivery fee</span><span>{cart.subtotal < 99 ? "₹9" : "Free"}</span></div>
          <div className="flex justify-between"><span className="text-ink-500">Example platform fee</span><span>₹18</span></div>
          <p className="text-xs text-ink-500">Illustration only: a shared trip could waive delivery and split the platform fee between up to 3 orders. These are not real charges.</p>
        </div>
        <div className="mt-4 rounded-xl bg-orange-50 p-3">
          <div className="flex justify-between text-sm"><span>Example if no pool forms</span><strong>₹{cart.subtotal + (cart.subtotal < 99 ? 9 : 0) + 18}</strong></div>
          {poolingEligible ? (
            <div className="mt-1 flex justify-between text-sm text-emerald-800"><span>If a pool forms</span><strong>₹{cart.subtotal + 6}–₹{cart.subtotal + 9}</strong></div>
          ) : (
            <div className="mt-1 flex justify-between gap-2 text-xs text-ink-500"><span>Sharing estimate</span><span>Unavailable for this basket size</span></div>
          )}
        </div>
        <p className="mt-3 text-[11px] text-ink-500">All fees above are examples only. This preview does not take payment or place a real delivery order.</p>
        {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
        <button disabled={busy} className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-brand-500 py-3 font-semibold text-white disabled:opacity-60">
          {busy ? "Placing…" : "Place simulated order"} {!busy && <ArrowRight className="h-4 w-4" />}
        </button>
      </aside>
    </form>
  );
}
