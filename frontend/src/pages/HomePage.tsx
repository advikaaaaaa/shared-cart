import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { api } from "../services/api";
import { useCart } from "../hooks/useCart";
import type { CatalogItem } from "../types";

function placeholder(type: string) {
  const hue = Math.abs([...type].reduce((s, c) => s + c.charCodeAt(0), 0)) % 40;
  return `hsl(${18 + hue} 55% 92%)`;
}

export function HomePage() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("all");
  const [disclaimer, setDisclaimer] = useState("");
  const [categories, setCategories] = useState<string[]>([]);
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const cart = useCart();

  useEffect(() => {
    setLoading(true);
    api
      .catalog(q, category)
      .then((d) => {
        setDisclaimer(d.disclaimer);
        setCategories(d.categories);
        setItems(d.items);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [q, category]);

  return (
    <div>
      <section className="grid gap-8 rounded-3xl border border-stone-200 bg-white p-8 md:grid-cols-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-600">SharedCart</p>
          <h1 className="mt-2 font-display text-4xl leading-tight text-ink-900">
            Smarter Food Delivery Through Intelligent Order Pooling
          </h1>
          <p className="mt-4 text-ink-700">
            Order from this sample grocery catalogue. Compatible nearby orders can share a simulated delivery trip,
            reducing unnecessary runs — without pretending a match exists until one actually arrives.
          </p>
        </div>
        <div className="rounded-2xl bg-brand-50 p-5 text-sm text-ink-700">
          <p className="font-semibold text-ink-900">How pooling works here</p>
          <p className="mt-2">
            After checkout, the operations engine scores whether waiting is worthwhile, then only confirms a pool if a
            later simulated order is compatible. This catalogue is grocery SKUs from the capstone table, not live
            restaurant menus.
          </p>
        </div>
      </section>

      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <label className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-ink-500" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search items or categories"
            className="w-full rounded-xl border border-stone-200 bg-white py-2.5 pl-9 pr-3 text-sm outline-none focus:border-brand-500"
          />
        </label>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded-xl border border-stone-200 bg-white px-3 py-2.5 text-sm"
        >
          <option value="all">All categories</option>
          {categories.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      </div>

      <p className="mt-4 text-xs text-ink-500">{disclaimer}</p>
      {error && <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      {loading && <p className="mt-8 text-sm text-ink-500">Loading catalogue…</p>}

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((item) => (
          <article key={item.item_id} className="flex flex-col rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
            <div
              className="mb-3 flex h-28 items-center justify-center rounded-xl text-sm font-medium text-ink-700"
              style={{ background: placeholder(item.item_type) }}
            >
              {item.item_type}
            </div>
            <p className="text-xs text-ink-500">{item.item_id}</p>
            <h3 className="mt-1 font-medium text-ink-900">{item.item_type}</h3>
            <p className="mt-auto pt-3 font-display text-xl">₹{item.item_price}</p>
            <button
              onClick={() => cart.add(item)}
              className="mt-3 rounded-xl bg-brand-500 py-2 text-sm font-semibold text-white hover:bg-brand-600"
            >
              Add to cart
            </button>
          </article>
        ))}
      </div>
    </div>
  );
}
