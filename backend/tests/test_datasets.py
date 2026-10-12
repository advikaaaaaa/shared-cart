from backend.app.ml.catalog import load_or_build_catalog
from backend.app.paths import BIGMART_CSV, CATALOG_CSV


def test_catalog_loads_from_source_or_clean_file():
    df = load_or_build_catalog()
    assert len(df) > 100
    for col in ("item_id", "item_type", "item_price"):
        assert col in df.columns
    assert df.item_price.min() > 0
    assert CATALOG_CSV.exists() or BIGMART_CSV.exists()


def test_catalog_does_not_invent_restaurants():
    df = load_or_build_catalog()
    assert "restaurant" not in df.columns.str.lower()
    assert "rating" not in df.columns.str.lower()
