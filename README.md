# SharedCart — Smarter Food Delivery Through Intelligent Order Pooling

SharedCart is a capstone web application that combines a sample grocery storefront with an ML-powered **order-pooling** operations system. Compatible nearby orders can share a simulated delivery trip. The catalogue, demand, and partners are **simulated** from the original notebook — they are not live restaurant data.

## What was already in this workspace

- `CapstoneProject.ipynb` — original Colab notebook (cleaning, event simulation, 23 features, RF/XGB/LR, utility policy)
- Backend FastAPI services for prediction, causal event replay, and WAIT / POOL / DISPATCH
- `data/source/bigmart_train.csv` — BlinkIT / BigMart grocery table used to rebuild the catalogue

This repository now also includes the React storefront, operations UI, artefact generator, tests, and local run instructions.

## Features

**Customer**

- A vibrant grocery storefront with search, category filters, paged product results, cart, simulated checkout, confirmation, and tracking
- A past-data ML forecast that reports its probability independently from the operations wait policy; it uses the current time of day and recent checkout activity when available
- Demo price estimates: ₹9 solo delivery below ₹99, waived delivery for a pool, and an ₹18 platform fee shared across a pool of up to three orders
- Per-order access keys protect order details; customer responses omit area identifiers and other customers' order IDs

**Operations**

- Separate admin sign-in and a distinct operations workspace with plain-language sample metrics
- Event replay (next event, start/pause/reset, speed) using `orders_events.csv`
- Pools can include up to three compatible orders; a pool closes at its cap or at the ML-selected wait limit
- Causal candidate matching (no future events)
- Real `model.pkl` predictions
- Decision engine: WAIT / POOL / DISPATCH with a waiting-time cap
- Dashboard, pooling simulator, model evaluation, impact comparison, dataset explorer

Checkout orders appear in the same simulation as dataset events.

## Architecture

```
frontend (React + Vite + TypeScript + Tailwind)  →  /api  →  FastAPI
                                                              ├── SQLite (app/simulation state)
                                                              ├── data/*.csv (historical / simulated ML data)
                                                              └── models/model.pkl (sklearn pipeline)
```

Grid cells are **synthetic 300 m zones**. Distance is Chebyshev cell distance, not a road route.

## Datasets

| File | Role |
|---|---|
| `data/source/bigmart_train.csv` | Original grocery catalogue source |
| `data/item_catalog_clean.csv` | One row per item, mean MRP |
| `data/orders_events.csv` | Simulated orders; `t` is **simulated minutes** |
| `data/training_dataset_final.csv` | 15 wait×radius rows per small order; target `partner_found` |
| `models/model.pkl` | Best sklearn pipeline (usually Random Forest, 23 features) |
| `models/model_meta.json` | Feature list, waits, radii, versions |
| `data/sharedcart.db` | App orders, predictions, decisions, and hashed per-order access keys (not the CSV sources) |

Default generation is a **lite** scale (20 days × 400 orders/day, seed 42, same process as the notebook) so a laptop can train locally. Use `--full` for the notebook’s 65 × 1200 volume.

## ML workflow

1. Past-only features + wait/radius scenarios  
2. Train LR, Random Forest, XGBoost on `split==train` (by day)  
3. Report metrics on `split==test`  
4. Serve the saved pipeline once at process start  
5. Simulated small orders wait only when the best ML window exceeds the model's held-out partner rate (12.32%); offline policy comparisons still use **utility** `E[saving] − λ E[delay]`

`partner_found` = another **different-user** small order arrives in the chosen radius within `wait_minutes`. A high probability is **not** proof that a partner exists in the live player.

## Simulation

- Events are sorted by `t` and released only when the clock reaches them  
- Duplicate CSV ids are ignored  
- Reset clears simulation rows; checkout orders can be kept  
- Playback delay = Δt / speed  

## Decision policy (notebook assumptions, not “optimal”)

- Fee **₹40**, free-delivery threshold **₹149**, delay cost **λ = ₹2 / min**, detour **2 min per grid cell**, max wait **15 min**  
- **WAIT** — the best ML chance cleared the wait threshold and the selected window has time remaining
- **POOL** — a played candidate is compatible and feasible  
- **DISPATCH** — the ML wait threshold was not met, a match is infeasible, or the wait cap is hit

The customer-facing ₹99 / ₹9 / ₹18 figures are a separate prototype pricing illustration. They are not collected and do not replace the notebook's ₹149 / ₹40 training-policy assumptions. Checkout assigns its anonymous sample area internally; the customer does not enter a synthetic grid cell or address.

## Limitations

- Grocery catalogue, not prepared meals  
- No GPS, riders, or real restaurants  
- Lite scale differs in volume from the Colab run  
- Best fixed rule on the test set in the notebook is slightly optimistic for that baseline  
- Simulated rupees are not commercial P&L  

## Windows PowerShell setup

```powershell
cd C:\Users\hp\OneDrive\Desktop\sharedcart

# Backend (once)
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe scripts\generate_artefacts.py
# Optional notebook-scale rebuild:
# .\.venv\Scripts\python.exe scripts\generate_artefacts.py --full --force

# Frontend (once)
cd frontend
npm install
cd ..
```

### Start backend

```powershell
cd C:\Users\hp\OneDrive\Desktop\sharedcart
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs  
Health: http://127.0.0.1:8000/api/health  

### Start frontend

```powershell
cd C:\Users\hp\OneDrive\Desktop\sharedcart\frontend
npm run dev
```

Open http://127.0.0.1:5173 — Vite proxies `/api` to port 8000.

Copy `.env.example` to `.env` only if you need overrides.

### Admin console

Set `SHAREDCART_ADMIN_USERNAME`, `SHAREDCART_ADMIN_PASSWORD`, and a unique `SHAREDCART_ADMIN_SECRET` of at least 32 characters in `.env` before starting the backend. Do not commit real credentials. `SHAREDCART_COOKIE_SECURE=false` is for local HTTP development; set it to `true` behind HTTPS. Open `/admin/login` to enter the separate operations workspace. Operations APIs return `401` without the signed, HTTP-only admin session cookie. If admin credentials are not configured, sign-in is disabled.

Customers do not see an Operations link. Each simulated checkout gets a random access key; only its SHA-256 hash is stored in SQLite. The key stays in the browser tab's session storage and is sent only as a request header for that order's confirmation/tracking. Customer order routes return `404` without the right key. This is a prototype privacy boundary—not account authentication for a production delivery service.

## Tests

```powershell
cd C:\Users\hp\OneDrive\Desktop\sharedcart
.\.venv\Scripts\python.exe -m pytest -q
```

## Manual demo script

1. Open SharedCart storefront  
2. Browse / search the grocery catalogue  
3. Add items and review the simulated checkout estimate (no address or payment required)
4. Open confirmation and tracking  
5. Sign in at `/admin/login`, then use Operations → Simulation → **Next event** (or Start for playback)
6. Dashboard should list the checkout order and dataset orders  
7. Pooling Simulator → Run prediction on a small order  
8. Confirm candidates / compatibility / WAIT|POOL|DISPATCH are separate  
9. Model Evaluation and Pooling Impact (offline + live)

## Troubleshooting

| Issue | What to try |
|---|---|
| `model_loaded: false` | Run `scripts\generate_artefacts.py` |
| Empty catalogue | Ensure `data/source/bigmart_train.csv` exists |
| Frontend 404 on `/api` | Start uvicorn on port 8000 first |
| Simulation `total_events = 0` | Generate artefacts; then Reset |
| Slow full rebuild | Default lite scale; `--full` is large |

Resetting the simulation does **not** delete `data/*.csv` or `models/model.pkl`.
