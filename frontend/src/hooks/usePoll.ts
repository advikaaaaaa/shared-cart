import { useEffect, useState } from "react";

export function usePoll<T>(fn: () => Promise<T>, ms = 1500, enabled = true) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    const tick = async () => {
      try {
        const v = await fn();
        if (alive) {
          setData(v);
          setError(null);
        }
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : "Request failed");
      }
    };
    tick();
    const id = setInterval(tick, ms);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [fn, ms, enabled]);

  return { data, error, setData };
}
