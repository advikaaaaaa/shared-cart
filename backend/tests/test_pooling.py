from backend.app.pooling.engine import (
    PolicyConfig,
    compatibility_check,
    decide,
    detour_minutes,
    fee_saving,
)


def test_fee_saving_full_waiver():
    assert fee_saving(80, 80) == 40.0


def test_fee_saving_partial():
    s = fee_saving(50, 50)
    assert abs(s - 40 * 50 / 100) < 1e-9


def test_detour_is_labelled_grid_proxy():
    assert detour_minutes(2, 2.0) == 4.0


def test_compatibility_requires_different_user():
    cand = {
        "order_id": 2,
        "user": 1,
        "waited_minutes": 3,
        "grid_distance": 1,
        "value": 60,
    }
    k = compatibility_check(1, cand, 8, PolicyConfig())
    assert k["feasible"] is False
    k2 = compatibility_check(9, cand, 8, PolicyConfig())
    assert k2["feasible"] is True


def test_wait_pool_dispatch_outcomes():
    cand = {
        "order_id": 2,
        "user": 8,
        "waited_minutes": 4,
        "grid_distance": 1,
        "value": 90,
        "t": 10,
    }
    pooled = decide(
        elapsed_wait=4,
        chosen_wait=8,
        chosen_radius=600,
        probability=0.9,
        candidates=[cand],
        focal_user=1,
        focal_value=70,
    )
    assert pooled.action == "POOL"
    assert pooled.partner_order_id == 2

    waiting = decide(
        elapsed_wait=2,
        chosen_wait=8,
        chosen_radius=600,
        probability=0.9,
        candidates=[],
        focal_user=1,
        focal_value=70,
    )
    assert waiting.action == "WAIT"

    dispatched = decide(
        elapsed_wait=15,
        chosen_wait=8,
        chosen_radius=600,
        probability=0.99,
        candidates=[],
        focal_user=1,
        focal_value=70,
    )
    assert dispatched.action == "DISPATCH"
    assert "waiting time" in dispatched.reason.lower() or "maximum" in dispatched.reason.lower()

    now = decide(
        elapsed_wait=0,
        chosen_wait=None,
        chosen_radius=None,
        probability=0.1,
        candidates=[],
        focal_user=1,
        focal_value=70,
    )
    assert now.action == "DISPATCH"


def test_high_probability_is_not_a_match():
    d = decide(
        elapsed_wait=1,
        chosen_wait=10,
        chosen_radius=900,
        probability=0.99,
        candidates=[],
        focal_user=1,
        focal_value=40,
    )
    assert d.action == "WAIT"
    assert d.partner_order_id is None
