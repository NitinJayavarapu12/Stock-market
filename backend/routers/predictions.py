import uuid
import threading
from fastapi import APIRouter, HTTPException, BackgroundTasks
from data.fetcher import fetch_stock_history
from models.predictor import predict_all_horizons
from backend.serializers import prediction_to_json
from config.settings import HISTORY_DAYS_PREDICTION

router = APIRouter(prefix="/api/predictions", tags=["predictions"])

# In-memory job store (fine for single-user tool; resets on server restart)
_jobs: dict = {}
_lock = threading.Lock()


def _run_prediction(job_id: str, symbol: str):
    try:
        df = fetch_stock_history(symbol, days=HISTORY_DAYS_PREDICTION)
        if df is None or df.empty:
            with _lock:
                _jobs[job_id] = {"status": "error", "error": f"No data for {symbol}", "symbol": symbol}
            return
        results = predict_all_horizons(df, symbol)
        serialized = {label: prediction_to_json(result) for label, result in results.items()}
        with _lock:
            _jobs[job_id] = {"status": "done", "result": serialized, "symbol": symbol}
    except Exception as e:
        with _lock:
            _jobs[job_id] = {"status": "error", "error": str(e), "symbol": symbol}


@router.post("/{symbol}/start")
def start_prediction(symbol: str, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {"status": "pending", "result": None, "symbol": symbol}
    background_tasks.add_task(_run_prediction, job_id, symbol)
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
def poll_prediction(job_id: str):
    with _lock:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
