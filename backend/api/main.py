import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Allow imports from backend/relayer when running from backend/api.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from api.relayer_service import RelayerService  # noqa: E402

relayer = RelayerService(tick_interval_s=1.0)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await relayer.start()
    yield
    await relayer.stop()


app = FastAPI(
    title="cotton.xyz relayer API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cotton-relayer", "environment": "testnet"}


@app.get("/api/market/latest")
async def market_latest():
    latest = relayer.latest
    if latest is None:
        return {"ready": False}
    return {"ready": True, "data": latest}


@app.get("/api/pairs")
async def list_pairs():
    from relayer.pairs import PAIRS

    return {"pairs": list(PAIRS.values()), "default": "US/USDC"}


@app.websocket("/ws/market")
async def ws_market(websocket: WebSocket):
    await websocket.accept()
    queue = relayer.subscribe()
    try:
        # Send snapshot immediately so clients don't hang before first tick
        if relayer.latest is not None:
            await websocket.send_text(json.dumps(relayer.latest))
        while True:
            payload = await queue.get()
            await websocket.send_text(json.dumps(payload))
    except WebSocketDisconnect:
        pass
    finally:
        relayer.unsubscribe(queue)
