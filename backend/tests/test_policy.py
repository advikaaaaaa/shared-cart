from backend.app.analytics.policy import live_impact
from backend.app.pooling.engine import choose_wait_radius, PolicyConfig


def test_live_impact_empty():
    out = live_impact([])
    assert out["orders"] == 0
    assert out["pooling_rate"] == 0


def test_live_impact_from_records():
    recs = [
        {"action": "POOL", "elapsed_wait": 4, "delay": 6, "saving": 40, "waited_without_match": False},
        {"action": "DISPATCH", "elapsed_wait": 15, "delay": 15, "saving": 0, "waited_without_match": True},
    ]
    out = live_impact(recs)
    assert out["pooled"] == 1
    assert out["pooling_rate"] == 0.5
    assert out["estimated_savings_total"] == 40


def test_choose_wait_dispatches_when_all_scores_nonpositive():
    cfg = PolicyConfig(lam=50.0)
    probs = {(w, r): 0.01 for w in cfg.waits for r in cfg.radii}
    mean = {(w, r): float(w) for w in cfg.waits for r in cfg.radii}
    assert choose_wait_radius(probs, 40, 10, mean, cfg) is None
