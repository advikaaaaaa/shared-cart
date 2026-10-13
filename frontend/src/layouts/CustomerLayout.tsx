import { Link, NavLink, Outlet } from "react-router-dom";
import { ShoppingBag } from "lucide-react";
import { Logo } from "../components/Logo";
import { useCart } from "../hooks/useCart";

export function CustomerLayout() {
  const { count } = useCart();
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-stone-200 bg-[#fffdf8]/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Link to="/">
            <Logo />
          </Link>
          <nav className="flex items-center gap-3 text-sm">
            <NavLink to="/" className={({ isActive }) => isActive ? "hidden font-semibold text-emerald-800 sm:block" : "hidden text-ink-700 hover:text-emerald-800 sm:block"}>Shop</NavLink>
            <Link to="/cart" className="relative flex items-center gap-2 rounded-full bg-[#183c30] px-4 py-2.5 text-white transition hover:bg-emerald-900">
              <ShoppingBag className="h-4 w-4" />
              <span className="hidden text-xs font-semibold sm:block">Your bag</span>
              {count > 0 && (
                <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-orange-500 px-1 text-[11px] text-white">
                  {count}
                </span>
              )}
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
        <Outlet />
      </main>
      <footer className="border-t border-stone-200 bg-white py-5 text-center text-xs text-ink-500">
        SharedCart · Everyday savings, shared trips. Concept demo only—no live orders or payments.
      </footer>
    </div>
  );
}
