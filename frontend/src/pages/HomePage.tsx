import { useEffect, useState } from "react";
import { ArrowRight, Leaf, Search, ShieldCheck, Sparkles, Truck } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import { useCart } from "../hooks/useCart";
import type { CatalogItem } from "../types";

const categoryColors = [
  "from-lime-200 to-emerald-100",
  "from-amber-200 to-orange-100",
  "from-sky-200 to-cyan-100",
  "from-rose-200 to-orange-100",
  "from-violet-200 to-fuchsia-100",
];

export function HomePage() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("all");
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [disclaimer, setDisclaimer] = useState("");
  const [categories, setCategories] = useState<string[]>([]);
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const cart = useCart();

  useEffect(() => {
    setLoading(true);
    let current = true;
    api.catalog(q, category, page)
      .then((d) => {
        if (!current) return;
        setDisclaimer(d.disclaimer);
        setCategories(d.categories);
        setItems(d.items);
        setTotalItems(d.count);
        setError(null);
      })
      .catch((e: Error) => { if (current) setError(e.message); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [q, category, page]);

  return (
    <div className="pb-12">
      <section className="relative isolate overflow-hidden rounded-[2rem] bg-[#183c30] px-6 py-9 text-white shadow-xl shadow-emerald-950/10 sm:px-10 sm:py-12 lg:px-14">
        <div className="absolute -right-24 -top-24 -z-10 h-80 w-80 rounded-full bg-lime-300/15 blur-2xl" />
        <div className="absolute bottom-0 right-[24%] -z-10 h-40 w-40 rounded-full bg-orange-300/10 blur-2xl" />
        <div className="grid items-center gap-10 lg:grid-cols-[1.15fr_.85fr]">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-semibold text-lime-200">
              <Sparkles className="h-3.5 w-3.5" /> LITTLE BASKETS, BETTER TOGETHER
            </p>
            <h1 className="mt-5 max-w-2xl font-display text-4xl leading-[1.05] tracking-tight sm:text-6xl">
              Your everyday basket deserves a <span className="text-lime-300">lighter</span> trip.
            </h1>
            <p className="mt-5 max-w-xl text-sm leading-6 text-emerald-50/80 sm:text-base">
              Pick up the groceries you need. We use a privacy-first, ML-powered forecast to see whether a nearby order could share the journey.
            </p>
            <a href="#shop" className="mt-7 inline-flex items-center gap-2 rounded-full bg-lime-300 px-5 py-3 text-sm font-bold text-emerald-950 transition hover:bg-lime-200">
              Find your favourites <ArrowRight className="h-4 w-4" />
            </a>
          </div>
          <div className="relative mx-auto w-full max-w-sm rounded-[1.75rem] bg-[#f7f4e9] p-5 text-emerald-950 shadow-2xl shadow-black/20 sm:p-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-[.18em] text-emerald-700">The shared-trip idea</p>
                <p className="mt-2 font-display text-2xl">Small basket. A potentially lighter trip.</p>
              </div>
              <span className="rounded-2xl bg-lime-200 p-3"><Leaf className="h-5 w-5" /></span>
            </div>
            <div className="mt-6 space-y-3">
              <div className="flex items-center gap-3 rounded-xl bg-white p-3">
                <span className="grid h-9 w-9 place-items-center rounded-full bg-orange-100 text-sm">🧺</span>
                <div className="flex-1"><p className="text-sm font-semibold">Your basket</p><p className="text-xs text-stone-500">Only your items are visible to you</p></div>
                <span className="text-xs font-bold">PRIVATE</span>
              </div>
              <div className="flex justify-center"><span className="h-5 border-l-2 border-dashed border-emerald-300" /></div>
              <div className="flex items-center gap-3 rounded-xl bg-emerald-100 p-3">
                <span className="grid h-9 w-9 place-items-center rounded-full bg-emerald-200"><Truck className="h-4 w-4" /></span>
                <div className="flex-1"><p className="text-sm font-semibold">One nearby delivery run</p><p className="text-xs text-emerald-900/70">Only when a compatible order arrives in simulation</p></div>
                <span className="text-xs font-bold text-emerald-800">UP TO 3</span>
              </div>
            </div>
            <p className="mt-4 text-[11px] leading-relaxed text-stone-500">Concept preview only: zones, orders, and savings are simulated. No live delivery is arranged.</p>
          </div>
        </div>
      </section>

      <section className="mt-7 grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-stone-200 bg-white p-4"><p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Under ₹99</p><p className="mt-1 font-display text-xl">₹9 solo delivery*</p></div>
        <div className="rounded-2xl border border-stone-200 bg-white p-4"><p className="text-xs font-semibold uppercase tracking-wide text-stone-500">If a pool forms</p><p className="mt-1 font-display text-xl">Delivery fee waived*</p></div>
        <div className="rounded-2xl border border-stone-200 bg-white p-4"><p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Your privacy</p><p className="mt-1 font-display text-xl">Basket stays yours</p></div>
      </section>

      <section id="shop" className="mt-11 scroll-mt-24">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[.16em] text-brand-600">Good things, close by</p>
            <h2 className="mt-1 font-display text-3xl text-ink-900">Your grocery picks</h2>
          </div>
          <label className="relative block w-full sm:max-w-xs">
            <Search className="absolute left-3 top-3 h-4 w-4 text-stone-400" />
            <input
              value={q}
              onChange={(e) => { setQ(e.target.value); setPage(1); }}
              placeholder="Search the catalogue"
              aria-label="Search groceries"
              className="w-full rounded-full border border-stone-200 bg-white py-2.5 pl-9 pr-4 text-sm outline-none transition focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
            />
          </label>
        </div>

        <div className="mt-5 flex gap-2 overflow-x-auto pb-1">
          {["all", ...categories].map((c) => (
            <button key={c} onClick={() => { setCategory(c); setPage(1); }} aria-pressed={category === c} className={`whitespace-nowrap rounded-full px-4 py-2 text-xs font-semibold transition ${category === c ? "bg-[#183c30] text-white" : "border border-stone-200 bg-white text-ink-700 hover:border-emerald-300"}`}>
              {c === "all" ? "Everything" : c}
            </button>
          ))}
        </div>

        <p className="mt-3 flex items-center gap-1.5 text-[11px] text-ink-500"><ShieldCheck className="h-3.5 w-3.5" /> {disclaimer}</p>
        {error && <p role="alert" className="mt-5 rounded-xl bg-red-50 p-3 text-sm text-red-800">{error}</p>}
        {loading && <p className="mt-8 text-sm text-ink-500">Finding your groceries…</p>}
        {!loading && !error && items.length === 0 && <p className="mt-8 text-sm text-ink-500">No groceries found. Try another search.</p>}
        {!loading && !error && items.length > 0 && <p className="mt-4 text-xs text-ink-500">Showing {(page - 1) * 12 + 1}–{Math.min(page * 12, totalItems)} of {totalItems} groceries</p>}

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {items.map((item, index) => (
            <article key={item.item_id} className="group flex flex-col overflow-hidden rounded-2xl border border-stone-200 bg-white p-3.5 transition hover:-translate-y-0.5 hover:border-emerald-300 hover:shadow-lg hover:shadow-emerald-950/5">
              <div className={`relative mb-3 flex h-32 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br ${categoryColors[index % categoryColors.length]}`}>
                <span className="absolute -right-4 -top-5 h-24 w-24 rounded-full border-[14px] border-white/30" />
                <span className="relative grid h-16 w-16 place-items-center rounded-2xl bg-white/70 text-3xl shadow-sm">{item.item_type.slice(0, 1).toUpperCase()}</span>
                <span className="absolute bottom-2 left-2 rounded-full bg-white/80 px-2 py-1 text-[10px] font-semibold text-emerald-950">{item.item_type}</span>
              </div>
              <p className="text-[10px] uppercase tracking-wide text-stone-400">{item.item_id}</p>
              <h3 className="mt-0.5 line-clamp-2 min-h-10 text-sm font-semibold text-ink-900">{item.item_type}</h3>
              <div className="mt-auto flex items-center justify-between pt-3">
                <span className="font-display text-xl font-semibold">₹{item.item_price}</span>
                <button onClick={() => cart.add(item)} className="rounded-lg border border-emerald-700 px-4 py-2 text-xs font-bold text-emerald-800 transition hover:bg-emerald-800 hover:text-white" aria-label={`Add ${item.item_type} to cart`}>
                  Add +
                </button>
              </div>
            </article>
          ))}
        </div>
        {totalItems > 12 && (
          <nav aria-label="Grocery pages" className="mt-6 flex items-center justify-center gap-3">
            <button disabled={page <= 1 || loading} onClick={() => setPage((current) => current - 1)} className="rounded-full border border-stone-300 bg-white px-4 py-2 text-sm font-semibold text-ink-800 disabled:opacity-40">Previous</button>
            <span className="text-sm text-ink-600">Page {page} of {Math.ceil(totalItems / 12)}</span>
            <button disabled={page >= Math.ceil(totalItems / 12) || loading} onClick={() => setPage((current) => current + 1)} className="rounded-full border border-stone-300 bg-white px-4 py-2 text-sm font-semibold text-ink-800 disabled:opacity-40">Next</button>
          </nav>
        )}
      </section>

      <footer className="mt-10 flex flex-col gap-2 border-t border-stone-200 pt-5 text-[11px] text-ink-500 sm:flex-row sm:justify-between">
        <span>*Fee examples only. This concept takes no payment and arranges no real delivery.</span>
        <Link to="/cart" className="font-semibold text-emerald-800">Review your bag ({cart.count}) →</Link>
      </footer>
    </div>
  );
}
