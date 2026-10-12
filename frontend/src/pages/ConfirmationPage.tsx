import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../services/api";
import { StatusBadge } from "../components/StatusBadge";
import type { Order } from "../types";

export function ConfirmationPage() {
  const { id } = useParams();
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api
      .order(Number(id))
      .then((d) => setOrder(d.order))
      .catch((e) => setError(e.message));
  }, [id]);

  if (error) return <p className="text-red-700">{error}</p>;
  if (!order) return <p>Loading confirmation…</p>;

  return (
    <div className="mx-auto max-w-lg rounded-2xl border border-stone-200 bg-white p-6">
      <p className="text-sm text-emerald-700">Order received (simulation)</p>
      <h1 className="mt-1 font-display text-3xl">#{order.order_id}</h1>
      <p className="mt-2 text-sm text-ink-500">Placement time (sim minutes): {order.t?.toFixed(2)}</p>
      <p className="mt-1">
        Status: <StatusBadge value={order.status} />
      </p>
      <p className="mt-4 font-display text-2xl">₹{order.value}</p>
      <ul className="mt-4 space-y-1 text-sm">
        {(order.items || []).map((it) => (
          <li key={it.item_id}>
            {it.item_type || it.item_id} × {it.quantity} — ₹{it.unit_price}
          </li>
        ))}
      </ul>
      <Link to={`/orders/${order.order_id}/track`} className="mt-6 inline-block rounded-xl bg-brand-500 px-4 py-2 text-sm font-semibold text-white">
        Track this order
      </Link>
    </div>
  );
}
