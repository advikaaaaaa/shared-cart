import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import { useCart } from "../hooks/useCart";
import type { Zone } from "../types";

export function CheckoutPage() {
  const cart = useCart();
  const nav = useNavigate();
  const [zones, setZones] = useState<Zone[]>([]);
  const [cell, setCell] = useState(44);
  const [name, setName] = useState("Guest");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.catalog().then((d) => {
      setZones(d.zones);
      if (d.zones.length) setCell(d.zones[0].cell);
    });
  }, []);

  if (cart.lines.length === 0) {
    return <p className="text-sm text-ink-500">Add items before checkout.</p>;
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.placeOrder({
        cell,
        customer_name: name,
        items: cart.lines.map((l) => ({
          item_id: l.item_id,
          item_type: l.item_type,
          unit_price: l.item_price,
          quantity: l.quantity,
        })),
      });
      cart.clear();
      nav(`/orders/${res.order.order_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="mx-auto max-w-xl space-y-4 rounded-2xl border border-stone-200 bg-white p-6">
      <h1 className="font-display text-2xl">Simulated checkout</h1>
      <p className="text-sm text-ink-500">
        No payment gateway. Grid cells are synthetic 300 m zones from the capstone simulation — not GPS addresses.
      </p>
      <label className="block text-sm">
        Name
        <input className="mt-1 w-full rounded-xl border px-3 py-2" value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <label className="block text-sm">
        Delivery grid cell
        <select className="mt-1 w-full rounded-xl border px-3 py-2" value={cell} onChange={(e) => setCell(Number(e.target.value))}>
          {zones.map((z) => (
            <option key={z.cell} value={z.cell}>
              {z.label}
            </option>
          ))}
        </select>
      </label>
      <p className="font-display text-2xl">Total ₹{cart.subtotal}</p>
      {error && <p className="text-sm text-red-700">{error}</p>}
      <button disabled={busy} className="w-full rounded-xl bg-brand-500 py-2.5 font-semibold text-white disabled:opacity-60">
        {busy ? "Placing…" : "Place simulated order"}
      </button>
    </form>
  );
}
