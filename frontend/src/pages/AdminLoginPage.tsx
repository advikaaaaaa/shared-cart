import { useState, type FormEvent } from "react";
import { ArrowRight, KeyRound, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Logo } from "../components/Logo";
import { api } from "../services/api";

export function AdminLoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.adminLogin(username, password);
      navigate("/operations", { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Admin sign-in failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="grid min-h-screen place-items-center bg-[#101e1a] px-4 py-10">
      <section className="w-full max-w-md rounded-[1.75rem] border border-white/10 bg-[#fffdf8] p-7 shadow-2xl sm:p-9">
        <Logo />
        <div className="mt-8 flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-900"><KeyRound className="h-5 w-5" /></div>
        <p className="mt-6 text-xs font-bold uppercase tracking-[.18em] text-emerald-800">Private workspace</p>
        <h1 className="mt-2 font-display text-3xl text-ink-900">Operations sign in</h1>
        <p className="mt-2 text-sm leading-relaxed text-ink-500">Authorized administrators only. Customer order details and simulation controls stay behind this sign-in.</p>
        <form onSubmit={submit} className="mt-7 space-y-4">
          <label className="block text-sm font-semibold text-ink-700">
            Admin ID
            <input autoComplete="username" required value={username} onChange={(e) => setUsername(e.target.value)} className="mt-1.5 w-full rounded-xl border border-stone-300 bg-white px-3 py-3 font-normal outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100" />
          </label>
          <label className="block text-sm font-semibold text-ink-700">
            Password
            <input autoComplete="current-password" required type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1.5 w-full rounded-xl border border-stone-300 bg-white px-3 py-3 font-normal outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100" />
          </label>
          {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-800">{error}</p>}
          <button disabled={busy} className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#183c30] py-3 text-sm font-bold text-white hover:bg-emerald-900 disabled:opacity-60">
            {busy ? "Checking access…" : "Sign in"} {!busy && <ArrowRight className="h-4 w-4" />}
          </button>
        </form>
        <p className="mt-5 flex items-start gap-2 text-[11px] leading-relaxed text-ink-500">
          <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          Admin credentials are configured by the operator in the backend environment. No demo password is built into the app.
        </p>
      </section>
    </main>
  );
}
