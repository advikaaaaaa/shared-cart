import { useEffect, useState } from "react";
import { Link, Navigate, NavLink, Outlet, useNavigate } from "react-router-dom";
import { Logo } from "../components/Logo";
import { api } from "../services/api";

const links = [
  { to: "/operations", label: "Dashboard", end: true },
  { to: "/operations/simulation", label: "Simulation" },
  { to: "/operations/simulator", label: "Pooling Simulator" },
  { to: "/operations/evaluation", label: "Model Evaluation" },
  { to: "/operations/impact", label: "Pooling Impact" },
  { to: "/operations/data", label: "Dataset Explorer" },
];

export function OpsLayout() {
  const navigate = useNavigate();
  const [auth, setAuth] = useState<"checking" | "valid" | "invalid">("checking");
  const [signOutError, setSignOutError] = useState<string | null>(null);

  useEffect(() => {
    api.adminSession()
      .then((r) => setAuth(r.authenticated ? "valid" : "invalid"))
      .catch(() => setAuth("invalid"));
  }, []);

  const signOut = async () => {
    try {
      await api.adminLogout();
      navigate("/admin/login", { replace: true });
    } catch (e) {
      setSignOutError(e instanceof Error ? e.message : "Could not sign out");
    }
  };

  if (auth === "checking") return <main className="grid min-h-screen place-items-center bg-[#101e1a] text-sm text-white">Verifying admin session…</main>;
  if (auth === "invalid") return <Navigate to="/admin/login" replace />;

  return (
    <div className="min-h-screen bg-[#f2f4f1]">
      <div className="flex min-h-screen">
        <aside className="relative hidden w-64 shrink-0 bg-[#101e1a] text-white md:block">
          <div className="border-b border-white/10 p-5">
            <Logo compact />
            <p className="mt-4 inline-flex rounded-full bg-lime-300/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[.16em] text-lime-200">Admin workspace</p>
          </div>
          <nav className="flex flex-col gap-1 px-3 py-5 text-sm">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                className={({ isActive }) =>
                  `rounded-xl px-3 py-2.5 transition ${isActive ? "bg-lime-300 font-semibold text-emerald-950" : "text-emerald-50/75 hover:bg-white/10 hover:text-white"}`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="absolute bottom-5 flex w-64 flex-col gap-2 px-4">
            <Link to="/" className="rounded-xl border border-white/10 px-3 py-2 text-sm text-emerald-50/80 hover:bg-white/10">← Customer storefront</Link>
            <button onClick={signOut} className="rounded-xl px-3 py-2 text-left text-sm text-rose-200 hover:bg-rose-200/10">Sign out</button>
          </div>
        </aside>
        <div className="flex-1">
          <div className="border-b border-stone-200 bg-white px-3 py-3 md:hidden">
            <div className="flex items-center justify-between">
              <Logo compact />
              <button onClick={signOut} className="text-xs font-semibold text-rose-700">Sign out</button>
            </div>
            <nav className="mt-3 flex gap-2 overflow-x-auto text-xs">
              {links.map((l) => <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => `whitespace-nowrap rounded-full px-3 py-1.5 ${isActive ? "bg-emerald-900 text-white" : "border border-stone-200 text-ink-700"}`}>{l.label}</NavLink>)}
            </nav>
          </div>
          <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
            {signOutError && <p role="alert" className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-800">{signOutError}</p>}
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
