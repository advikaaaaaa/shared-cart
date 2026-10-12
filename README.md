# Food Order Pooling System

A beginner-friendly web demo. It predicts whether a compatible nearby food order may arrive within five minutes, checks whether two orders can be pooled, and recommends **wait** or **dispatch**.

This uses **Python**, **Streamlit**, **pandas**, and **scikit-learn**. The CSV data is synthetic (made-up) so the demo can run without a real restaurant database.

## Folder layout

- `data/` — sample orders (CSV)
- `models/` — saved machine-learning model
- `src/` — loading data, features, pooling rules, training, and the wait/dispatch decision
- `app/` — Streamlit web page

## Setup

From the `capstone` folder:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If `venv` is already created, only activate it, then install packages if needed.

## Train the model (optional)

The first time you open the app it can train automatically. To train by hand:

```powershell
.\venv\Scripts\python.exe src\train_model.py
```

## Run the web demo

```powershell
.\venv\Scripts\python.exe -m streamlit run app\streamlit_app.py
```

Then open the local URL shown in the terminal (usually `http://localhost:8501`).
