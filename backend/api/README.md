# cotton.xyz relayer API (MVP)

Minimal FastAPI service exposing live oracle/mark updates from the reference relayer.

## Endpoints

- `GET /health` — service health
- `GET /api/market/latest` — latest relayer snapshot (REST)
- `WS /ws/market` — live JSON stream (1s cadence)

## Run locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Open the frontend panel:

- `http://localhost:3000/app.html` (with static server)
- API default: `http://localhost:8000`

## Notes

- Uses simulated order book + periodic external feed outage for fallback testing.
- Replace `sim_feed.py` adapters with live matching engine + ICE oracle in Phase 2.
