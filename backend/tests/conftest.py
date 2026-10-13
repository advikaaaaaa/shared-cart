import pytest


@pytest.fixture(autouse=True)
def isolate_app_database(tmp_path, monkeypatch):
    from backend.app.database import db
    from backend.app.simulation import runtime

    if runtime._RUNTIME is not None:
        runtime._RUNTIME.pause()
    runtime._RUNTIME = None
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "sharedcart-test.db")
    yield
    if runtime._RUNTIME is not None:
        runtime._RUNTIME.pause()
    runtime._RUNTIME = None
