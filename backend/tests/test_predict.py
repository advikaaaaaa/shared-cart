import pytest

from backend.app.ml.predict import ModelNotAvailable, load_meta, load_pipeline, predict_from_base, predict_proba_row
from backend.app.paths import MODEL_PKL


def test_model_load_or_clear_error():
    if not MODEL_PKL.exists():
        with pytest.raises(ModelNotAvailable):
            load_pipeline()
        return
    pipe = load_pipeline()
    assert hasattr(pipe, "predict_proba")
    meta = load_meta()
    assert meta["features"]
    assert meta.get("target") == "partner_found"


def test_missing_features_rejected():
    if not MODEL_PKL.exists():
        pytest.skip("model.pkl not generated yet")
    with pytest.raises(ValueError, match="Missing"):
        predict_proba_row({"hour": 12})


def test_prediction_output_validity():
    if not MODEL_PKL.exists():
        pytest.skip("model.pkl not generated yet")
    meta = load_meta()
    base = {
        "hour": 13,
        "day_of_week": 2,
        "is_weekend": 0,
        "is_peak_hour": 1,
        "grid_row": 4,
        "grid_col": 4,
        "zone_type": "commercial",
        "order_value": 80,
        "n_items": 2,
        "orders_in_cell_last_15min": 3,
        "avg_orders_in_cell_this_hour": 4.0,
        "user_past_order_count": 2,
        "user_small_order_ratio": 0.4,
        "small_orders_300m_last_15min": 1,
        "small_orders_600m_last_15min": 2,
        "small_orders_900m_last_15min": 4,
    }
    row, pred = predict_from_base(base, 8, 600)
    assert 0.0 <= pred["probability"] <= 1.0
    assert pred["predicted_class"] in (0, 1)
    assert pred["features_used"] == meta["features"]
    for f in meta["features"]:
        assert f in row
