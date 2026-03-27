import json
import asyncio
import threading
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from data.fetcher import fetch_stock_history
from data.processor import get_latest_stats
from models.indicators import get_indicator_summary
from models.predictor import predict_all_horizons
from ai.gemini_client import stream_stock_insight

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/insight/{symbol}")
async def ai_insight(symbol: str):
    """SSE stream of Gemini AI analysis for a stock."""

    async def generate():
        loop = asyncio.get_event_loop()

        df = await loop.run_in_executor(None, fetch_stock_history, symbol)
        if df is None or df.empty:
            err_msg = json.dumps({"text": f"No data found for {symbol}."})
            yield f"data: {err_msg}\n\n"
            yield "data: [DONE]\n\n"
            return

        stats = get_latest_stats(df)
        indicators = get_indicator_summary(df)

        # Notify client that predictions are being computed (takes 30-60s)
        progress_msg = json.dumps({"text": "🔄 Running price predictions, please wait...\n\n"})
        yield f"data: {progress_msg}\n\n"

        predictions = await loop.run_in_executor(None, predict_all_horizons, df, symbol)
        company = symbol.replace(".NS", "").replace(".BO", "")

        # Stream Gemini tokens progressively via a queue
        queue: asyncio.Queue = asyncio.Queue()

        def _producer():
            try:
                for chunk in stream_stock_insight(symbol, company, stats, indicators, predictions):
                    asyncio.run_coroutine_threadsafe(queue.put(chunk), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        thread = threading.Thread(target=_producer, daemon=True)
        thread.start()

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield f"data: {json.dumps({'text': chunk})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
