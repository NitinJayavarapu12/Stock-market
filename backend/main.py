import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from backend.routers import market, stocks, trending, watchlist, ai, predictions, chat, alerts


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Stock Insights API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market.router)
app.include_router(stocks.router)
app.include_router(trending.router)
app.include_router(watchlist.router)
app.include_router(ai.router)
app.include_router(predictions.router)
app.include_router(chat.router)
app.include_router(alerts.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve React build in production
dist_dir = ROOT / "frontend" / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")
