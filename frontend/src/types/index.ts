export type CatalogItem = {
  item_id: string;
  item_type: string;
  item_price: number;
  is_small_item?: number;
  price_band?: string;
};

export type Zone = {
  cell: number;
  grid_row: number;
  grid_col: number;
  zone_type: string;
  label: string;
};

export type CartLine = CatalogItem & { quantity: number };

export type SimStatus = {
  status: string;
  clock: number;
  event_index: number;
  total_events: number;
  speed: number;
  start_day: number;
  active_orders: number;
  waiting_orders: number;
  pooled_orders: number;
  dispatched_orders: number;
  customer_queued: number;
  simulation_label: string;
};

export type Order = {
  order_id: number;
  source?: string;
  status: string;
  value: number;
  cell: number;
  t: number;
  n_items: number;
  small?: number;
  decision?: string;
  reason?: string;
  probability?: number | null;
  wait_minutes?: number | null;
  radius_m?: number | null;
  partner_order_id?: number | null;
  elapsed_wait?: number;
  customer_name?: string;
  items?: { item_id: string; item_type?: string; unit_price: number; quantity: number }[];
  history?: { status: string; sim_t: number; note: string }[];
  placed_wallclock?: string;
};

export type Tracking = {
  order: Order;
  clock: number;
  stages: { key: string; label: string; done: boolean }[];
};
