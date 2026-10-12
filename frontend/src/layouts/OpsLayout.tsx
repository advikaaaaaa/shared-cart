import { NavLink, Outlet } from "react-router-dom";
import { Logo } from "../components/Logo";

const links = [
  { to: "/operations", label: "Dashboard", end: true },
  { to: "/operations/simulation", label: "Simulation" },
  { to: "/operations/simulator", label: "Pooling Simulator" },
  { to: "/operations/evaluation", label: "Model Evaluation" },
  { to: "/operations/impact", label: "Pooling Impact" },
  { to: "/operations/data", label: "Dataset Explorer" },
  { to: "/", label: "← Storefront" },
];

export function OpsLayout() {
  return (
    <div className="min-h-screen bg-[#f3efe9]">
      <div className="flex min-h-screen">
        <aside className="hidden w-60 shrink-0 border-r border-stone-200 bg-white md:block">
          <div className="p-4">
            <Logo compact />
            <p className="mt-3 text-[11px] uppercase tracking-wide text-ink-500">Operations</p>
          </div>
          <nav className="flex flex-col gap-1 px-3 pb-6 text-sm">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-2 ${isActive ? "bg-brand-50 font-semibold text-brand-700" : "text-ink-700 hover:bg-stone-50"}`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
        </aside>
        <div className="flex-1">
          <div className="flex gap-2 overflow-x-auto border-b border-stone-200 bg-white px-3 py-2 text-sm md:hidden">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} className="whitespace-nowrap rounded-full border px-3 py-1">
                {l.label}
              </NavLink>
            ))}
          </div>
          <main className="mx-auto max-w-6xl px-4 py-6">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
