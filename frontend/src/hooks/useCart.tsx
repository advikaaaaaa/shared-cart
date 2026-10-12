import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import type { CartLine, CatalogItem } from "../types";

const KEY = "sharedcart-cart";

function load(): CartLine[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

const CartCtx = createContext<{
  lines: CartLine[];
  add: (item: CatalogItem) => void;
  inc: (id: string) => void;
  dec: (id: string) => void;
  remove: (id: string) => void;
  clear: () => void;
  count: number;
  subtotal: number;
} | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const [lines, setLines] = useState<CartLine[]>(load);

  const persist = (next: CartLine[]) => {
    setLines(next);
    localStorage.setItem(KEY, JSON.stringify(next));
  };

  const api = useMemo(
    () => ({
      lines,
      add: (item: CatalogItem) => {
        const found = lines.find((l) => l.item_id === item.item_id);
        persist(
          found
            ? lines.map((l) => (l.item_id === item.item_id ? { ...l, quantity: l.quantity + 1 } : l))
            : [...lines, { ...item, quantity: 1 }],
        );
      },
      inc: (id: string) => persist(lines.map((l) => (l.item_id === id ? { ...l, quantity: l.quantity + 1 } : l))),
      dec: (id: string) =>
        persist(
          lines
            .map((l) => (l.item_id === id ? { ...l, quantity: l.quantity - 1 } : l))
            .filter((l) => l.quantity > 0),
        ),
      remove: (id: string) => persist(lines.filter((l) => l.item_id !== id)),
      clear: () => persist([]),
      count: lines.reduce((s, l) => s + l.quantity, 0),
      subtotal: lines.reduce((s, l) => s + l.item_price * l.quantity, 0),
    }),
    [lines],
  );

  return <CartCtx.Provider value={api}>{children}</CartCtx.Provider>;
}

export function useCart() {
  const ctx = useContext(CartCtx);
  if (!ctx) throw new Error("useCart must be inside CartProvider");
  return ctx;
}
