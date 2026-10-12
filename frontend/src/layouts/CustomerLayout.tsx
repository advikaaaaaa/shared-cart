import { Link, NavLink, Outlet } from "react-router-dom";
import { ShoppingBag } from "lucide-react";
import { Logo } from "../components/Logo";
import { useCart } from "../hooks/useCart";

const nav = [
  { to: "/", label: "Shop" },
  { to: "/operations", label: "Operations" },
];

export function CustomerLayout() {
  const { count } = useCart();
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-stone-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <Link to="/">
            <Logo />
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            {nav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  isActive ? "font-semibold text-brand-600" : "text-ink-700 hover:text-brand-600"
                }
              >
                {n.label}
              </NavLink>
            ))}
            <Link to="/cart" className="relative rounded-full border border-stone-200 p-2 hover:border-brand-500">
              <ShoppingBag className="h-5 w-5" />
              {count > 0 && (
                <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-brand-500 px-1 text-[11px] text-white">
                  {count}
                </span>
              )}
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
      <footer className="border-t border-stone-200 py-8 text-center text-xs text-ink-500">
        SharedCart — Smarter Food Delivery Through Intelligent Order Pooling. Simulated checkout; no payments.
      </footer>
    </div>
  );
}
