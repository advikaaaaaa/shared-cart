from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SOURCE_DIR = DATA_DIR / "source"
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"
DB_PATH = DATA_DIR / "sharedcart.db"

CATALOG_CSV = DATA_DIR / "item_catalog_clean.csv"
EVENTS_CSV = DATA_DIR / "orders_events.csv"
TRAINING_CSV = DATA_DIR / "training_dataset_final.csv"
BIGMART_CSV = SOURCE_DIR / "bigmart_train.csv"

MODEL_PKL = MODELS_DIR / "model.pkl"
MODEL_META = MODELS_DIR / "model_meta.json"
MODEL_COMPARISON = MODELS_DIR / "model_comparison.csv"
POLICY_CSV = REPORTS_DIR / "policy_comparison.csv"
SENSITIVITY_CSV = REPORTS_DIR / "sensitivity_results.csv"
FEATURE_IMPORTANCE_CSV = REPORTS_DIR / "permutation_importance.csv"
CONFUSION_CSV = REPORTS_DIR / "confusion_matrices.csv"
CALIBRATION_CSV = REPORTS_DIR / "calibration_curve.csv"
ZONE_AUC_CSV = REPORTS_DIR / "zone_auc.csv"


def ensure_dirs() -> None:
    for d in (DATA_DIR, SOURCE_DIR, MODELS_DIR, REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
