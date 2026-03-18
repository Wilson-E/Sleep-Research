# Sleep Score Backend (FastAPI)

## Run

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# put the CSVs in backend/data (already referenced by default)
uvicorn app.main:app --reload --port 8000
```

## Endpoints
- `GET /health`
- `POST /api/predict` — returns a 0–100 sleep score + breakdown.

## Data files expected
Place these in `backend/data/`:
- `financial_traders_data.csv`
- `Didikoglu_et_al_2023_PNAS_sleep.csv`

You can override paths with env vars `TRADERS_CSV` and `DIDIKOGLOU_CSV`.
