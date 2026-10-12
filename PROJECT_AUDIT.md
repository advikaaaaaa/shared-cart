# SharedCart — Project Audit

**Date:** 13 October 2026 (updated after application implementation)  
**Workspace inspected:** `C:\Users\hp\OneDrive\Desktop\sharedcart`  
**Original source:** `CapstoneProject.ipynb`. Application code, lite simulated CSVs, and a trained pipeline are generated locally from that notebook’s logic.

This audit records what the notebook actually does and what is present in the inspected workspace. The committed artefacts are generated from the notebook’s logic at the documented lite scale so the web app can use them locally.

---

## 1. What exists in the workspace

| Artefact | Present? | Notes |
|---|---|---|
| `CapstoneProject.ipynb` | Yes | Google Colab notebook (23 cells), ~1.0 MB including outputs |
| `data/source/bigmart_train.csv` | Yes | Source grocery catalogue used for the reproducible local build |
| `data/item_catalog_clean.csv` | Yes | Generated cleaned catalogue |
| `data/orders_events.csv` | Yes | Generated lite-scale simulated events |
| `data/training_dataset_final.csv` | Yes | Generated lite-scale training rows |
| `models/model.pkl` | Yes | Trained scikit-learn pipeline |
| `models/model_meta.json` | Yes | Feature and model metadata |
| `models/model_comparison.csv` | Yes | Held-out model comparison metrics |
| `reports/*.csv` | Yes | Generated evaluation and policy reports |
| `sensitivity_results.csv` | No | Not generated as a separate artefact by the local build |
| Web application | Yes | FastAPI backend, React/Vite frontend, and SQLite-backed app state |

**Implication:** the checked-in app artefacts include a trained model and are reproducible with `scripts/generate_artefacts.py`. The runtime SQLite database is local state and is intentionally excluded from version control.

---

## 2. Where the original data comes from

Cell 0 uploads a local Excel file in Colab:

`Tableau BlinkIT Grocery Project U16955293080 (4).xlsx`

Printed columns match the public **BigMart Sales / BlinkIT grocery** schema:

`Item_Identifier`, `Item_Weight`, `Item_Fat_Content`, `Item_Visibility`, `Item_Type`, `Item_MRP`, `Outlet_Identifier`, `Outlet_Establishment_Year`, `Outlet_Size`, `Outlet_Location_Type`, `Outlet_Type`, `Item_Outlet_Sales`

**This is a grocery item catalogue, not prepared restaurant meals.** The storefront must present it as a sample grocery catalogue.

Cleaning (cell 1):

- One row per `Item_Identifier`
- `item_type` = first `Item_Type`
- `item_price` = mean `Item_MRP`, rounded to integer rupees
- `is_small_item` if price &lt; 75
- `price_band` bins: `&lt;50`, `50-100`, `100-150`, `150+`

Printed catalogue: **1,559 items**, mean price **₹141**.

Outlet, sales, visibility, and fat-content columns are dropped. They are **not** used by the ML model.

---

## 3. How simulated order events are generated

Orders are **fully synthetic** (seed `42`). They are not historical restaurant trips.

| Parameter | Value |
|---|---|
| Grid | 10 × 10 cells, 300 m each (3 km × 3 km simulated area) |
| Small-order threshold | ₹149 (below this, delivery fee applies; pooling candidate) |
| Warm-up days | 7 (history only; not in training rows) |
| Total days | 65 |
| Train last day | 48 (days 7–48 train, 49–63 test) |
| Target orders / day | 1,200 (Poisson around zone-hour intensity) |
| Hours | 07:00–23:00 |
| Users | 4,000, assigned to cells with zone weights |
| Wait options | 2, 5, 8, 10, 15 minutes |
| Radii | 300, 600, 900 m → Chebyshev cell distance 0, 1, 2 |

Zone types (with Gaussian noise): `commercial`, `dense_residential`, `normal_residential`, `quiet`.

Each order samples 1–4 catalogue items (probabilities 0.65 / 0.22 / 0.10 / 0.03). Time `t` is **simulated minutes** from the start of day 0 (`day * 1440 + hour * 60 + uniform(0, 60)`).

Printed result: **78,514 orders**, **36.5% small**, events file shape **(78514, 10)**.

Event columns: `t`, `day`, `hour`, `dow`, `cell`, `user`, `value`, `n_items`, `order_id`, `small`.

There are **no GPS coordinates**. Grid cells are simulated identifiers only.

---

## 4. Training examples and target

Only **small** orders (`value < 149`) after warm-up and before the last buffer day become focal orders.

For each focal order the notebook builds **past-only features**, then expands to **15 scenario rows** (5 waits × 3 radii).

**Target `partner_found`:** 1 if another small order from a **different user** arrives in the chosen radius within `wait_minutes`. Same-user orders are ignored. The label looks **forward in time**; features do not.

Printed dataset: **375,675 rows**, **25,045 unique small orders**, partner-found rate **0.320**. Labels are monotone in wait and radius (verified in the notebook).

Split: `day <= 48` → `train` (277,635 rows, positive rate 0.321); else `test` (98,040 rows, 0.318). The `day` column is then dropped from the table.

---

## 5. Features

**Original (18):**  
`hour`, `day_of_week`, `is_weekend`, `is_peak_hour`, `grid_row`, `grid_col`, `zone_type`, `order_value`, `n_items`, `orders_in_cell_last_15min`, `avg_orders_in_cell_this_hour`, `user_past_order_count`, `user_small_order_ratio`, `small_orders_300m_last_15min`, `small_orders_600m_last_15min`, `small_orders_900m_last_15min`, `wait_minutes`, `radius_m`

**Engineered extras:**  
`hour_sin`, `hour_cos`, `recent_in_chosen_radius`, `expected_arrivals`, `busy_ratio` (clipped at train 99th percentile, printed cap **10.44**), `wait_x_cells` (wait × 1/9/25 cells), `is_dense_zone`

**Dropped as weak:** `small_orders_300m_last_15min`, `is_weekend` (still used indirectly via `recent_in_chosen_radius` when radius is 300 m).

**Final (23):**  
`hour`, `day_of_week`, `is_peak_hour`, `grid_row`, `grid_col`, `order_value`, `n_items`, `orders_in_cell_last_15min`, `avg_orders_in_cell_this_hour`, `user_past_order_count`, `user_small_order_ratio`, `small_orders_600m_last_15min`, `small_orders_900m_last_15min`, `wait_minutes`, `radius_m`, `hour_sin`, `hour_cos`, `recent_in_chosen_radius`, `expected_arrivals`, `busy_ratio`, `wait_x_cells`, `is_dense_zone`, `zone_type`

Identifiers never used as model inputs: `order_id`, `user_id`, `split`, `grid_cell_id`.

---

## 6. Algorithms and preprocessing

Each model is a scikit-learn `Pipeline`:

- `OneHotEncoder(handle_unknown="ignore")` on `zone_type`
- Numeric columns: `StandardScaler` for logistic regression; passthrough for trees
- Classifier

| Model | Settings |
|---|---|
| Logistic Regression | `max_iter=2000`, scaled numerics |
| Random Forest | 100 trees, `max_depth=12`, `min_samples_leaf=20`, `random_state=42` |
| XGBoost | 200 trees, `max_depth=6`, `lr=0.1`, `subsample=0.8`, `colsample_bytree=0.8` |

Baselines: class-mean probability; wait/radius lookup of train partner rate.

---

## 7. Train / validation / test

- Feature selection and all fitting use **train only**.
- Reported metrics use **held-out test rows**.
- There is **no separate validation fold** for hyperparameter search; hyperparameters are fixed in code.
- Rows are **not grouped by `order_id` at evaluation time**: 15 scenarios from the same order can appear in the same split (the split is by calendar day, so an order’s 15 rows stay together). Test-set AUC can be slightly optimistic relative to a fully independent order, but there is **no train/test leakage of the same order**.

---

## 8. Metrics printed in the notebook

Test ROC-AUC:

| Model | Original (18) | Final (23) |
|---|---|---|
| Logistic Regression | 0.8430 | 0.8452 |
| Random Forest | 0.8518 | **0.8539** |
| XGBoost | 0.8536 | 0.8531 |

**Best saved pipeline:** Random Forest + Final (23).

Zone-wise AUC (best model): commercial 0.856, dense 0.849, normal 0.850, quiet 0.829.

Accuracy, precision, recall, F1, log-loss, Brier, and confusion matrices were computed in `score()` and written to `model_comparison.csv`, which was not in the workspace. They must be regenerated, not invented.

---

## 9. Wait-time and search-radius policy

Not a single probability threshold.

**Economic assumptions (stated as assumptions in the notebook):**

- Delivery fee `FEE = ₹40`
- Combined basket ≥ ₹149 → full fee waived on the partner (saving `FEE`); otherwise saving `FEE * partner_value / combined`
- Delay cost `LAM = ₹2` per minute (sensitivity over 0.25–12)
- Extra delay `DETOUR_MIN = 2` minutes per Chebyshev cell between the two orders (sensitivity 0, 2, 5, 8)
- Maximum wait `MAXW = 15` minutes

**Smart policy:** for each test order, score every (wait, radius) combo as  
`expected_saving − λ × expected_delay`.  
If the best score ≤ 0 → **dispatch now**; else pick that combo.

Expected delay-if-found and expected partner values are estimated from **train** orders only. Realised outcomes on test use the actual first partner.

The notebook’s own comment: the “best fixed rule” is picked **on the test set** (`15 min / 900 m`), so that baseline is **favourable** to the fixed rule.

Printed smart policy (λ = 2): 7.1% dispatched immediately; most chosen combos use 900 m.

Grid Chebyshev distance is **not** a road-route feasibility proof. The notebook treats it as a simulated detour proxy.

---

## 10–11. Saved pipeline and metadata

The notebook writes:

```text
joblib.dump(fitted[best], "model.pkl")
model_meta.json = {features, waits, radii, best_model}
```

Those files were **not** in the workspace, so **no claim of a loadable model is valid until regeneration succeeds**. After training, metadata must include `FINAL_FEATURES`, busy-ratio cap, sklearn/xgboost versions, and the cost constants.

---

## 12. Leakage and unrealistic assumptions

**Acceptable / intended**

- Features use only the past 15 minutes and prior-day hourly averages.
- User counts are updated after the current order is recorded (`pn` is the count before this order).
- Live playback must not use unplayed future events for matching, even though training labels look ahead.

**Caveats (must be labelled in the product)**

1. Catalogue, demand, locations, and partners are **simulated**.
2. “Distance” is grid-cell Chebyshev distance, not roads.
3. No restaurants, riders, or GPS traces exist in the data.
4. Multiple scenario rows per order share features; metrics are still useful but not independent Bernoulli trials.
5. Best-fixed-rule comparison on test is slightly optimistic for the fixed baseline.
6. BlinkIT Excel was not supplied; regeneration uses the public BigMart train table with the same schema and 1,559 item IDs.
7. Peak hours are hardcoded `(12, 13, 19, 20, 21)`.
8. Same-cell neighbours include the order’s own cell; “300 m radius” is the home cell only.

---

## 13. Implementation gaps (before this application)

1. No web UI, API, or database.
2. No causal live event player (notebook policy evaluation is batch/offline).
3. No checkout path that builds features for a new cart.
4. No WAIT / POOL / DISPATCH engine that re-evaluates as time advances.
5. Model and CSVs missing from disk.
6. Colab `files.upload` / `files.download` are not runnable locally.

---

## 14. What the application must reuse

- Seed-42 event simulation and 15-scenario labelling
- Final 23 features and the trained sklearn pipeline
- Utility policy `E[saving] − λ E[delay]`, not “probability ⇒ pooled”
- ₹40 fee, ₹149 threshold, λ and detour as configurable assumptions
- Honest grocery catalogue from the cleaned item table
