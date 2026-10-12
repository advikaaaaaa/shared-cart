"""Causal event replay with pooling decisions. Future CSV rows are never visible to the matcher."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from backend.app.analytics.policy import live_impact
from backend.app.database.db import get_conn, init_db
from backend.app.ml.constants import GRID, MAXW, RADII, THRESHOLD, WAITS
from backend.app.ml.live_features import EventIndex, causal_candidates
from backend.app.ml.predict import ModelNotAvailable, predict_from_base
from backend.app.ml.simulate import build_zones, engineer_row
from backend.app.paths import EVENTS_CSV
from backend.app.pooling.engine import PolicyConfig, choose_wait_radius, decide, fee_saving

CUSTOMER_ID_BASE = 900_000


class SimulationRuntime:
    def __init__(self, events_df: pd.DataFrame | None = None, start_day: int = 7) -> None:
        self.lock = threading.RLock()
        self.events = pd.DataFrame()
        self.zone = build_zones(np.random.default_rng(42))
        self.live = EventIndex()
        self.orders: dict[int, dict[str, Any]] = {}
        self.customer_queue: list[dict[str, Any]] = []
        self.mean_delay: dict[tuple[int, int], float] = {(w, r): float(w) for r in RADII for w in WAITS}
        self.es_scale_by_value: dict[int, float] = {}
        self._auto_thread: threading.Thread | None = None
        self._stop_auto = threading.Event()
        self._seen_event_ids: set[int] = set()
        init_db()
        if events_df is not None:
            self.events = events_df.sort_values("t").reset_index(drop=True)
        else:
            self._load_events()
        self.reset(persist_customers=True, start_day=start_day)

    def _load_events(self) -> None:
        if not EVENTS_CSV.exists():
            self.events = pd.DataFrame(
                columns=["t", "day", "hour", "dow", "cell", "user", "value", "n_items", "order_id", "small"]
            )
            return
        df = pd.read_csv(EVENTS_CSV)
        self.events = df.sort_values("t").reset_index(drop=True)

    def status(self) -> dict[str, Any]:
        with self.lock:
            active = [o for o in self.orders.values() if o["status"] in ("placed", "evaluating", "waiting")]
            pooled = sum(1 for o in self.orders.values() if o["status"] == "pooled")
            dispatched = sum(1 for o in self.orders.values() if o["status"] in ("dispatched", "delivered"))
            waiting = sum(1 for o in self.orders.values() if o["status"] == "waiting")
            return {
                "status": self._status,
                "clock": self.clock,
                "event_index": self.event_index,
                "total_events": int(len(self.events)),
                "speed": self.speed,
                "start_day": self.start_day,
                "active_orders": len(active),
                "waiting_orders": waiting,
                "pooled_orders": pooled,
                "dispatched_orders": dispatched,
                "customer_queued": len(self.customer_queue),
                "simulation_label": "Simulated minutes (dataset field t), not wall-clock time.",
            }

    def reset(self, persist_customers: bool = True, start_day: int = 7) -> dict[str, Any]:
        with self.lock:
            self._stop_auto.set()
            self._status = "idle"
            self.speed = 8.0
            self.start_day = start_day
            self.clock = 0.0
            self.event_index = 0
            self.live = EventIndex()
            kept = []
            if persist_customers:
                kept = [o for o in self.orders.values() if o.get("source") == "checkout"]
            self.orders = {}
            self.customer_queue = []
            self._seen_event_ids = set()
            if not self.events.empty:
                warmup = self.events[self.events.day < start_day]
                for r in warmup.itertuples(index=False):
                    self.live.observe(r)
                nxt = self.events[self.events.day >= start_day]
                self.event_index = int(nxt.index.min()) if len(nxt) else int(len(self.events))
                if self.event_index < len(self.events):
                    self.clock = float(self.events.iloc[self.event_index].t)
            with get_conn() as conn:
                conn.execute("DELETE FROM decisions")
                conn.execute("DELETE FROM predictions")
                conn.execute("DELETE FROM status_history")
                if persist_customers:
                    conn.execute("DELETE FROM order_items WHERE order_id < ?", (CUSTOMER_ID_BASE,))
                    conn.execute("DELETE FROM app_orders WHERE source != 'checkout'")
                else:
                    conn.execute("DELETE FROM order_items")
                    conn.execute("DELETE FROM app_orders")
                    kept = []
                conn.execute(
                    "UPDATE sim_state SET status=?, clock=?, event_index=?, speed=?, start_day=?, total_events=? WHERE id=1",
                    ("idle", self.clock, self.event_index, self.speed, start_day, int(len(self.events))),
                )
            for o in kept:
                o["status"] = "placed"
                self.customer_queue.append(dict(o))
                self.orders[o["order_id"]] = o
            return self.status()

    def start(self) -> dict[str, Any]:
        with self.lock:
            if self._status == "running":
                return self.status()
            self._status = "running"
            self._stop_auto.clear()
            self._persist_status()
        t = threading.Thread(target=self._auto_loop, daemon=True)
        self._auto_thread = t
        t.start()
        return self.status()

    def pause(self) -> dict[str, Any]:
        with self.lock:
            self._status = "paused"
            self._stop_auto.set()
            self._persist_status()
            return self.status()

    def resume(self) -> dict[str, Any]:
        return self.start()

    def set_speed(self, speed: float) -> dict[str, Any]:
        with self.lock:
            self.speed = max(0.25, min(float(speed), 240.0))
            self._persist_status()
            return self.status()

    def step(self, n: int = 1) -> dict[str, Any]:
        last = None
        for _ in range(max(1, n)):
            last = self._step_one()
            if last.get("done"):
                break
        st = self.status()
        st["last_event"] = last
        return st

    def _auto_loop(self) -> None:
        while not self._stop_auto.is_set():
            with self.lock:
                if self._status != "running":
                    return
                wait_s = 0.05
                nxt = self._peek_next_t()
                if nxt is None:
                    self._status = "idle"
                    self._persist_status()
                    return
                dt = max(0.0, float(nxt) - self.clock)
                wait_s = min(1.5, dt / max(self.speed, 0.01)) if dt > 0 else 0.0
            if wait_s > 0:
                self._stop_auto.wait(wait_s)
                if self._stop_auto.is_set():
                    return
            self._step_one()

    def _peek_next_t(self) -> float | None:
        csv_t = (
            float(self.events.iloc[self.event_index].t)
            if self.event_index < len(self.events)
            else None
        )
        cq = [o for o in self.customer_queue if not o.get("ingested")]
        extra_t = min((float(o["t"]) for o in cq), default=None)
        opts = [x for x in (csv_t, extra_t) if x is not None]
        return min(opts) if opts else None

    def _step_one(self) -> dict[str, Any]:
        with self.lock:
            csv_row = None
            if self.event_index < len(self.events):
                csv_row = self.events.iloc[self.event_index]
            pending = sorted(
                [o for o in self.customer_queue if not o.get("ingested")],
                key=lambda o: float(o["t"]),
            )
            use_customer = False
            if csv_row is None and not pending:
                self._status = "idle"
                return {"done": True, "message": "No further events"}
            if pending and (csv_row is None or float(pending[0]["t"]) <= float(csv_row.t)):
                use_customer = True
                rec = pending[0]
                rec["ingested"] = True
                row_t = float(rec["t"])
            else:
                rec = csv_row
                row_t = float(rec.t)
                self.event_index += 1
            self.clock = row_t
            arrived = self._ingest_row(rec, source="checkout" if use_customer else "dataset")
            self._revisit_waiting()
            self._mark_delivered()
            self._persist_status()
            return {"done": False, "ingested": arrived}

    def _ingest_row(self, rec: Any, source: str) -> dict[str, Any]:
        if isinstance(rec, dict):
            order = dict(rec)
        else:
            order = {
                "order_id": int(rec.order_id),
                "source": source,
                "user_id": int(rec.user),
                "cell": int(rec.cell),
                "t": float(rec.t),
                "day": int(rec.day),
                "hour": int(rec.hour),
                "dow": int(rec.dow),
                "value": int(rec.value),
                "n_items": int(rec.n_items),
                "small": int(rec.small),
                "status": "placed",
            }
        oid = int(order["order_id"])
        if oid in self._seen_event_ids and source != "checkout":
            return self.orders.get(oid, order)
        self._seen_event_ids.add(oid)
        order.setdefault("source", source)
        order["status"] = "evaluating" if order.get("small") else "dispatched"
        order["elapsed_wait"] = 0.0
        order.setdefault("history", [])
        self._note(order, "placed", "Order entered the simulation")
        features = self.live.features_before(_Row(order), self.zone)
        order["base_features"] = features
        cfg = PolicyConfig()
        if not order.get("small"):
            order["status"] = "dispatched"
            order["decision"] = "DISPATCH"
            order["reason"] = "Order value meets the free-delivery threshold; pooling is not applied."
            self._note(order, "dispatched", order["reason"])
            self.live.observe(_Row(order))
            self.orders[oid] = order
            self._save_order(order)
            self._save_decision(order)
            return order

        probs = {}
        chosen = None
        best_p = None
        try:
            for w in WAITS:
                for r in RADII:
                    row, pred = predict_from_base(features, w, r)
                    probs[(w, r)] = pred["probability"]
                    self._save_prediction(oid, w, r, pred, row)
            est_saving = float(min(cfg.fee, cfg.fee * max(order["value"], 1) / max(order["value"] + 80, 1)))
            chosen = choose_wait_radius(probs, order["value"], est_saving, self.mean_delay, cfg)
            if chosen:
                best_p = probs[chosen]
        except ModelNotAvailable as exc:
            order["model_error"] = str(exc)
            chosen = (8, 600)
            best_p = None

        order["wait_minutes"], order["radius_m"] = (chosen if chosen else (None, None))
        order["probability"] = best_p
        order["probs"] = {f"{w}_{r}": p for (w, r), p in probs.items()}
        decision = decide(
            elapsed_wait=0.0,
            chosen_wait=order["wait_minutes"],
            chosen_radius=order["radius_m"],
            probability=best_p,
            candidates=[],
            focal_user=order["user_id"],
            focal_value=order["value"],
            cfg=cfg,
        )
        order["status"] = "waiting" if decision.action == "WAIT" else "dispatched"
        order["decision"] = decision.action
        order["reason"] = decision.reason
        self._note(order, order["status"], decision.reason)
        self.live.observe(_Row(order))
        self.orders[oid] = order
        self._save_order(order)
        self._save_decision(order, decision)
        return order

    def _revisit_waiting(self) -> None:
        cfg = PolicyConfig()
        for order in list(self.orders.values()):
            if order.get("status") != "waiting":
                continue
            elapsed = self.clock - float(order["t"])
            order["elapsed_wait"] = elapsed
            cands = causal_candidates(
                self.live,
                int(order["cell"]),
                float(order["t"]),
                int(order["user_id"]),
                int(order.get("radius_m") or 600),
                int(order.get("wait_minutes") or MAXW),
                self.clock,
            )
            cands = [c for c in cands if c["order_id"] != order["order_id"]]
            d = decide(
                elapsed_wait=elapsed,
                chosen_wait=order.get("wait_minutes"),
                chosen_radius=order.get("radius_m"),
                probability=order.get("probability"),
                candidates=cands,
                focal_user=order["user_id"],
                focal_value=order["value"],
                cfg=cfg,
            )
            if d.action == "POOL":
                order["status"] = "pooled"
                order["decision"] = "POOL"
                order["partner_order_id"] = d.partner_order_id
                order["reason"] = d.reason
                order["saving"] = d.expected_saving
                order["delay"] = d.expected_delay
                self._note(order, "pooled", d.reason)
                self._note(order, "dispatched", "Pooled pair released for simulated dispatch")
                order["status"] = "dispatched"
                partner = self.orders.get(d.partner_order_id)
                if partner and partner.get("status") in ("waiting", "evaluating", "placed"):
                    partner["status"] = "dispatched"
                    partner["decision"] = "POOL"
                    partner["partner_order_id"] = order["order_id"]
                    self._note(partner, "pooled", "Matched as pooling partner")
                    self._note(partner, "dispatched", "Pooled pair released for simulated dispatch")
                    self._save_order(partner)
                    self._save_decision(partner, d)
                self._save_order(order)
                self._save_decision(order, d)
            elif d.action == "DISPATCH":
                order["status"] = "dispatched"
                order["decision"] = "DISPATCH"
                order["reason"] = d.reason
                order["waited_without_match"] = elapsed > 0
                self._note(order, "dispatched", d.reason)
                self._save_order(order)
                self._save_decision(order, d)

    def _mark_delivered(self) -> None:
        for order in self.orders.values():
            if order.get("status") != "dispatched":
                continue
            dispatched_t = next(
                (h["sim_t"] for h in reversed(order.get("history", [])) if h.get("status") == "dispatched"),
                order.get("t"),
            )
            if self.clock - float(dispatched_t) >= 8:
                order["status"] = "delivered"
                self._note(order, "delivered", "Marked delivered in the simulation after a fixed 8-minute lag")
                self._save_order(order)

    def place_customer_order(
        self,
        items: list[dict[str, Any]],
        cell: int,
        customer_name: str = "Guest",
    ) -> dict[str, Any]:
        with self.lock:
            value = int(sum(int(i["unit_price"]) * int(i["quantity"]) for i in items))
            n_items = int(sum(int(i["quantity"]) for i in items))
            t = float(self.clock) if self.clock else (
                float(self.events.iloc[self.event_index].t) if self.event_index < len(self.events) else 0.0
            )
            day = int(t // 1440)
            hour = int((t % 1440) // 60)
            oid = CUSTOMER_ID_BASE + len([o for o in self.orders.values() if o.get("source") == "checkout"]) + 1
            order = {
                "order_id": oid,
                "source": "checkout",
                "user_id": 999999,
                "cell": int(cell),
                "t": t + 0.001,
                "day": day,
                "hour": hour,
                "dow": day % 7,
                "value": value,
                "n_items": n_items,
                "small": int(value < THRESHOLD),
                "status": "placed",
                "customer_name": customer_name,
                "items": items,
                "placed_wallclock": datetime.now(timezone.utc).isoformat(),
                "ingested": False,
            }
            self.orders[oid] = order
            self.customer_queue.append(order)
            self.customer_queue.sort(key=lambda x: x["t"])
            self._save_order(order)
            for it in items:
                with get_conn() as conn:
                    conn.execute(
                        "INSERT INTO order_items (order_id, item_id, item_type, unit_price, quantity) VALUES (?,?,?,?,?)",
                        (oid, it["item_id"], it.get("item_type"), int(it["unit_price"]), int(it["quantity"])),
                    )
            self._note(order, "placed", "Simulated checkout (no payment collected)")
            return order

    def get_order(self, order_id: int) -> dict[str, Any] | None:
        with self.lock:
            o = self.orders.get(int(order_id))
            if o:
                return o
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM app_orders WHERE order_id=?", (order_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            items = conn.execute("SELECT * FROM order_items WHERE order_id=?", (order_id,)).fetchall()
            hist = conn.execute(
                "SELECT status, sim_t, note FROM status_history WHERE order_id=? ORDER BY id",
                (order_id,),
            ).fetchall()
            d["items"] = [dict(i) for i in items]
            d["history"] = [dict(h) for h in hist]
            return d

    def list_orders(self, source: str | None = None, q: str | None = None, status: str | None = None, limit: int = 200):
        with self.lock:
            rows = list(self.orders.values())
        if source:
            rows = [r for r in rows if r.get("source") == source]
        if status:
            rows = [r for r in rows if r.get("status") == status]
        if q:
            qs = str(q)
            rows = [r for r in rows if qs in str(r.get("order_id"))]
        rows.sort(key=lambda r: r.get("t", 0), reverse=True)
        return [_public_order(r) for r in rows[:limit]]

    def tracking(self, order_id: int) -> dict[str, Any]:
        order = self.get_order(order_id)
        if not order:
            return {}
        status = order.get("status")
        stages = [
            {"key": "placed", "label": "Order placed", "done": True},
            {
                "key": "evaluating",
                "label": "Evaluating pooling opportunities",
                "done": status in ("evaluating", "waiting", "pooled", "dispatched", "delivered"),
            },
            {
                "key": "waiting",
                "label": "Waiting for a possible match",
                "done": status in ("waiting", "pooled", "dispatched", "delivered")
                and order.get("decision") in ("WAIT", "POOL", "DISPATCH"),
            },
            {
                "key": "pooled",
                "label": "Pooling confirmed",
                "done": order.get("decision") == "POOL" or status == "pooled",
            },
            {
                "key": "dispatched",
                "label": "Dispatched",
                "done": status in ("dispatched", "delivered"),
            },
            {
                "key": "delivered",
                "label": "Delivered in simulation",
                "done": status == "delivered",
            },
        ]
        return {"order": order, "stages": stages, "clock": self.clock}

    def dashboard(self) -> dict[str, Any]:
        with self.lock:
            recs = []
            for o in self.orders.values():
                if o.get("decision") in ("POOL", "DISPATCH", "WAIT"):
                    recs.append(
                        {
                            "action": o.get("decision"),
                            "elapsed_wait": o.get("elapsed_wait") or 0,
                            "delay": o.get("delay") or o.get("elapsed_wait") or 0,
                            "saving": o.get("saving") or 0,
                            "waited_without_match": o.get("waited_without_match", False),
                        }
                    )
            recent = sorted(self.orders.values(), key=lambda x: x.get("t", 0), reverse=True)[:25]
            by_status: dict[str, int] = {}
            by_zone: dict[str, int] = {}
            for o in self.orders.values():
                by_status[o.get("status", "?")] = by_status.get(o.get("status", "?"), 0) + 1
                z = str(self.zone[int(o["cell"])])
                by_zone[z] = by_zone.get(z, 0) + 1
            timeline = []
            for o in recent:
                for h in o.get("history", [])[-2:]:
                    timeline.append({"order_id": o["order_id"], **h})
            impact = live_impact(recs)
            return {
                "status": self.status(),
                "metrics": {
                    "introduced": len(self.orders),
                    "active": sum(1 for o in self.orders.values() if o["status"] in ("placed", "evaluating", "waiting")),
                    "waiting": sum(1 for o in self.orders.values() if o["status"] == "waiting"),
                    "pooled": sum(1 for o in self.orders.values() if o.get("decision") == "POOL"),
                    "dispatched_independent": sum(
                        1 for o in self.orders.values() if o.get("decision") == "DISPATCH"
                    ),
                    "pooling_rate": impact["pooling_rate"],
                    "avg_wait": impact["avg_wait"],
                    "estimated_savings": impact["estimated_savings_total"],
                },
                "impact": impact,
                "by_status": by_status,
                "by_zone": by_zone,
                "recent": [
                    {
                        "order_id": o["order_id"],
                        "status": o.get("status"),
                        "decision": o.get("decision"),
                        "t": o.get("t"),
                        "value": o.get("value"),
                        "cell": o.get("cell"),
                        "small": o.get("small"),
                        "source": o.get("source"),
                        "probability": o.get("probability"),
                    }
                    for o in recent
                ],
                "timeline": timeline[-40:],
            }

    def run_prediction(self, order_id: int, wait_minutes: int, radius_m: int) -> dict[str, Any]:
        with self.lock:
            order = self.orders.get(int(order_id))
            if not order:
                raise KeyError(order_id)
            base = order.get("base_features")
            if not base:
                base = self.live.features_before(_Row(order), self.zone)
            row, pred = predict_from_base(base, wait_minutes, radius_m)
            cands = causal_candidates(
                self.live,
                int(order["cell"]),
                float(order["t"]),
                int(order["user_id"]),
                int(radius_m),
                int(wait_minutes),
                self.clock,
            )
            cands = [c for c in cands if c["order_id"] != order["order_id"]]
            d = decide(
                elapsed_wait=max(0.0, self.clock - float(order["t"])),
                chosen_wait=wait_minutes,
                chosen_radius=radius_m,
                probability=pred["probability"],
                candidates=cands,
                focal_user=order["user_id"],
                focal_value=order["value"],
            )
            return {
                "order": {
                    "order_id": order["order_id"],
                    "value": order["value"],
                    "cell": order["cell"],
                    "t": order["t"],
                    "status": order["status"],
                    "small": order["small"],
                },
                "inputs": row,
                "prediction": pred,
                "observed_candidates": cands,
                "decision": d.__dict__,
                "clock": self.clock,
                "disclaimer": (
                    "Predicted partner_found probability is not evidence that a partner exists. "
                    "Candidates are only orders that have already been played."
                ),
            }

    def _note(self, order: dict[str, Any], status: str, note: str) -> None:
        entry = {"status": status, "sim_t": self.clock, "note": note}
        order.setdefault("history", []).append(entry)
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO status_history (order_id, status, sim_t, note) VALUES (?,?,?,?)",
                (order["order_id"], status, self.clock, note),
            )

    def _save_order(self, order: dict[str, Any]) -> None:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO app_orders (order_id, source, user_id, cell, t, day, hour, dow, value, n_items, small, status,
                    wait_minutes, radius_m, partner_order_id, placed_wallclock, customer_name)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(order_id) DO UPDATE SET
                    status=excluded.status, wait_minutes=excluded.wait_minutes, radius_m=excluded.radius_m,
                    partner_order_id=excluded.partner_order_id
                """,
                (
                    order["order_id"],
                    order.get("source", "dataset"),
                    order["user_id"],
                    order["cell"],
                    order["t"],
                    order["day"],
                    order["hour"],
                    order["dow"],
                    order["value"],
                    order["n_items"],
                    order["small"],
                    order.get("status", "placed"),
                    order.get("wait_minutes"),
                    order.get("radius_m"),
                    order.get("partner_order_id"),
                    order.get("placed_wallclock"),
                    order.get("customer_name"),
                ),
            )

    def _save_prediction(self, oid: int, w: int, r: int, pred: dict[str, Any], row: dict[str, Any]) -> None:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO predictions (order_id, wait_minutes, radius_m, probability, predicted_class, sim_t, feature_json) VALUES (?,?,?,?,?,?,?)",
                (
                    oid,
                    w,
                    r,
                    pred["probability"],
                    pred["predicted_class"],
                    self.clock,
                    json.dumps({k: row[k] for k in row if k in row}, default=str),
                ),
            )

    def _save_decision(self, order: dict[str, Any], decision=None) -> None:
        action = getattr(decision, "action", None) or order.get("decision") or "WAIT"
        key = f"{order['order_id']}:{action}:{round(self.clock, 4)}"
        with get_conn() as conn:
            try:
                conn.execute(
                    """INSERT INTO decisions (order_id, action, wait_minutes, radius_m, probability, partner_order_id,
                        saving, delay, elapsed_wait, reason, sim_t, unique_key) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        order["order_id"],
                        action,
                        order.get("wait_minutes"),
                        order.get("radius_m"),
                        order.get("probability"),
                        order.get("partner_order_id") or getattr(decision, "partner_order_id", None),
                        getattr(decision, "expected_saving", None) if decision else order.get("saving"),
                        getattr(decision, "expected_delay", None) if decision else order.get("delay"),
                        order.get("elapsed_wait") or 0,
                        getattr(decision, "reason", None) if decision else order.get("reason"),
                        self.clock,
                        key,
                    ),
                )
            except Exception:
                pass

    def _persist_status(self) -> None:
        with get_conn() as conn:
            conn.execute(
                "UPDATE sim_state SET status=?, clock=?, event_index=?, speed=?, start_day=?, total_events=? WHERE id=1",
                (self._status, self.clock, self.event_index, self.speed, self.start_day, int(len(self.events))),
            )


class _Row:
    def __init__(self, d: dict[str, Any]):
        self.order_id = d["order_id"]
        self.user = d["user_id"]
        self.cell = d["cell"]
        self.t = d["t"]
        self.day = d["day"]
        self.hour = d["hour"]
        self.dow = d["dow"]
        self.value = d["value"]
        self.n_items = d["n_items"]
        self.small = d["small"]


def _public_order(o: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "order_id",
        "source",
        "user_id",
        "cell",
        "t",
        "day",
        "hour",
        "dow",
        "value",
        "n_items",
        "small",
        "status",
        "wait_minutes",
        "radius_m",
        "partner_order_id",
        "decision",
        "reason",
        "probability",
        "elapsed_wait",
        "customer_name",
        "items",
        "placed_wallclock",
        "history",
        "saving",
        "delay",
        "waited_without_match",
        "model_error",
    )
    out = {}
    for k in keep:
        if k not in o:
            continue
        v = o[k]
        if hasattr(v, "item"):
            try:
                v = v.item()
            except Exception:
                v = v
        out[k] = v
    return out


_RUNTIME: SimulationRuntime | None = None
_RT_LOCK = threading.Lock()


def get_runtime() -> SimulationRuntime:
    global _RUNTIME
    with _RT_LOCK:
        if _RUNTIME is None:
            _RUNTIME = SimulationRuntime()
        return _RUNTIME


def reset_runtime_for_tests(events_df: pd.DataFrame | None = None, start_day: int = 0) -> SimulationRuntime:
    global _RUNTIME
    with _RT_LOCK:
        if _RUNTIME is not None:
            _RUNTIME.pause()
        _RUNTIME = SimulationRuntime(events_df=events_df, start_day=start_day)
        return _RUNTIME
