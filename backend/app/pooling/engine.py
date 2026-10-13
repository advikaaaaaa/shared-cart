"""Wait / pool / dispatch policy from the notebook, plus causal live matching.

Grid Chebyshev distance is a labelled simulated-proximity proxy, not a road route.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from backend.app.ml.constants import DETOUR_MIN, FEE, LAM, MAXW, RADII, THRESHOLD, WAITS

Action = Literal["WAIT", "POOL", "DISPATCH"]
MIN_PROBABILITY_TO_WAIT = 0.1232


def fee_saving(order_value: float, partner_value: float, fee: float = FEE, threshold: float = THRESHOLD) -> float:
    combined = order_value + partner_value
    if combined <= 0:
        return 0.0
    if combined >= threshold:
        return float(fee)
    return float(fee * partner_value / combined)


def detour_minutes(grid_distance: int, detour_per_cell: float = DETOUR_MIN) -> float:
    return float(detour_per_cell * grid_distance)


@dataclass
class PolicyConfig:
    fee: float = FEE
    threshold: float = THRESHOLD
    lam: float = LAM
    detour_min: float = DETOUR_MIN
    max_wait: int = MAXW
    waits: list[int] = field(default_factory=lambda: list(WAITS))
    radii: list[int] = field(default_factory=lambda: list(RADII.keys()))
    min_probability_to_wait: float = 0.0  # unused by default; notebook is utility-based
    max_pool_orders: int = 3


@dataclass
class Decision:
    action: Action
    wait_minutes: int | None
    radius_m: int | None
    probability: float | None
    expected_saving: float | None
    expected_delay: float | None
    net_score: float | None
    partner_order_id: int | None
    partner_value: float | None
    grid_distance: int | None
    simulated_detour_min: float | None
    reason: str
    candidates_considered: int
    elapsed_wait: float
    compatibility: list[dict[str, Any]] = field(default_factory=list)
    partner_order_ids: list[int] = field(default_factory=list)


def choose_wait_radius(
    probabilities: dict[tuple[int, int], float],
    order_value: float,
    expected_saving_if_found: float,
    mean_delay_if_found: dict[tuple[int, int], float],
    cfg: PolicyConfig,
) -> tuple[int, int] | None:
    """Notebook smart_choice: argmax E[saving]-λ E[delay]; None means dispatch now."""
    best_j = None
    best_score = 0.0
    for w in cfg.waits:
        for r in cfg.radii:
            p = float(probabilities.get((w, r), 0.0))
            es = expected_saving_if_found * p
            mt = float(mean_delay_if_found.get((w, r), w))
            ed = p * mt + (1 - p) * w
            score = es - cfg.lam * ed
            if score > best_score:
                best_score = score
                best_j = (w, r)
    return best_j


def choose_probability_window(
    probabilities: dict[tuple[int, int], float],
    min_probability: float = MIN_PROBABILITY_TO_WAIT,
) -> tuple[tuple[int, int] | None, tuple[int, int] | None, float]:
    """Return the best ML window and only recommend waiting above the held-out base rate."""
    if not probabilities:
        return None, None, 0.0
    best_window, best_probability = max(
        probabilities.items(), key=lambda scenario: (scenario[1], -scenario[0][0], -scenario[0][1])
    )
    if best_probability <= 0:
        return None, None, 0.0
    recommended = best_window if best_probability >= min_probability else None
    return recommended, best_window, float(best_probability)


def compatibility_check(
    focal_user: int,
    candidate: dict[str, Any],
    wait_minutes: int,
    cfg: PolicyConfig,
) -> dict[str, Any]:
    waited = float(candidate["waited_minutes"])
    dist = int(candidate["grid_distance"])
    within_wait = waited <= wait_minutes + 1e-9
    within_max = waited <= cfg.max_wait + 1e-9
    different_user = int(candidate["user"]) != int(focal_user)
    detour = detour_minutes(dist, cfg.detour_min)
    feasible = within_wait and within_max and different_user
    return {
        "order_id": candidate["order_id"],
        "waited_minutes": round(waited, 3),
        "grid_distance_cells": dist,
        "simulated_detour_min": round(detour, 3),
        "different_user": different_user,
        "within_wait": within_wait,
        "within_max_wait": within_max,
        "feasible": feasible,
        "note": "Grid Chebyshev distance is simulated proximity, not a road route.",
    }


def decide(
    *,
    elapsed_wait: float,
    chosen_wait: int | None,
    chosen_radius: int | None,
    probability: float | None,
    candidates: list[dict[str, Any]],
    focal_user: int,
    focal_value: float,
    cfg: PolicyConfig | None = None,
    force_dispatch: bool = False,
) -> Decision:
    """Causal live decision. Probability never implies a pool by itself."""
    cfg = cfg or PolicyConfig()
    comps = [
        compatibility_check(focal_user, c, chosen_wait or cfg.max_wait, cfg) for c in candidates
    ]
    feasible = []
    seen_users = {int(focal_user)}
    for candidate, check in zip(candidates, comps):
        candidate_user = int(candidate["user"])
        if check["feasible"] and candidate_user not in seen_users:
            feasible.append(candidate)
            seen_users.add(candidate_user)

    if force_dispatch:
        return Decision(
            "DISPATCH",
            chosen_wait,
            chosen_radius,
            probability,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "Forced dispatch (order is not small, or pooling is disabled).",
            len(candidates),
            elapsed_wait,
            comps,
        )

    if feasible and (
        chosen_wait is None
        or len(feasible) >= cfg.max_pool_orders - 1
        or elapsed_wait >= min(chosen_wait or cfg.max_wait, cfg.max_wait) - 1e-9
    ):
        partners = feasible[: max(1, cfg.max_pool_orders - 1)]
        partner = partners[0]
        dist = max(int(p["grid_distance"]) for p in partners)
        detour = detour_minutes(dist, cfg.detour_min)
        partner_value = sum(float(p["value"]) for p in partners)
        sav = fee_saving(focal_value, partner_value, cfg.fee, cfg.threshold)
        decision = Decision(
            "POOL",
            chosen_wait,
            chosen_radius,
            probability,
            sav,
            elapsed_wait + detour,
            sav - cfg.lam * (elapsed_wait + detour),
            int(partner["order_id"]),
            partner_value,
            dist,
            detour,
            "Compatible orders from different users were observed in the simulated radius. "
            "The pool closes at its participant cap or chosen wait limit; probability is not proof of a match.",
            len(candidates),
            elapsed_wait,
            comps,
        )
        decision.partner_order_ids = [int(p["order_id"]) for p in partners]
        return decision

    if feasible:
        return Decision(
            "WAIT",
            chosen_wait,
            chosen_radius,
            probability,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "A compatible order has arrived; keeping the pool open for more orders until its cap or chosen wait limit.",
            len(candidates),
            elapsed_wait,
            comps,
        )

    if chosen_wait is None:
        return Decision(
            "DISPATCH",
            None,
            None,
            probability,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "No wait was recommended for this order; dispatching without delay.",
            len(candidates),
            elapsed_wait,
            comps,
        )

    if elapsed_wait >= min(chosen_wait, cfg.max_wait) - 1e-9:
        return Decision(
            "DISPATCH",
            chosen_wait,
            chosen_radius,
            probability,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "Maximum waiting time reached without a feasible partner in the played event stream.",
            len(candidates),
            elapsed_wait,
            comps,
        )

    return Decision(
        "WAIT",
        chosen_wait,
        chosen_radius,
        probability,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        "Waiting under the configured policy. No feasible partner has arrived yet "
        "(a high predicted probability is not treated as a found match).",
        len(candidates),
        elapsed_wait,
        comps,
    )
