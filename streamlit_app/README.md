# Coffee Roasters Streamlit Dashboard

Run the dashboard locally:

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate   # use `.venv\Scripts\activate` on Windows
pip install -r streamlit_app/requirements.txt
```

2. Run the app:

```bash
streamlit run streamlit_app/app.py
```

Notes:
- The app expects the CSV file at `Data_sheet/sql Afficionado Coffee Roasters.csv` relative to the repository root.
- If your CSV lacks a `day_of_week` column, the dashboard will fallback to using `Time Bucket` for day-like breakdowns.
- Metric toggle switches between `Revenue` (uses `Revenu` column if present) and `Quantity` (uses `transaction_qty`).
