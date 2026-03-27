import json
from fastapi import APIRouter, HTTPException, Query
from data.fetcher import fetch_stock_history, search_stocks
from data.processor import get_latest_stats
from models.indicators import get_indicator_summary
from ui.charts import plot_candlestick_with_indicators
from backend.serializers import df_to_records
from config.settings import HISTORY_DAYS_DEFAULT, NIFTY_50_SYMBOLS

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/search")
def stock_search(q: str = Query(..., min_length=1), limit: int = 10):
    return search_stocks(q, top_n=limit)


@router.get("/nifty50")
def nifty50_symbols():
    return NIFTY_50_SYMBOLS


@router.get("/{symbol}/history")
def stock_history(symbol: str, days: int = HISTORY_DAYS_DEFAULT):
    df = fetch_stock_history(symbol, days=days)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
    return df_to_records(df)


@router.get("/{symbol}/indicators")
def stock_indicators(symbol: str):
    df = fetch_stock_history(symbol)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
    return {
        "stats": get_latest_stats(df),
        "indicators": get_indicator_summary(df),
    }


@router.get("/{symbol}/chart-json")
def stock_chart_json(symbol: str, days: int = HISTORY_DAYS_DEFAULT):
    df = fetch_stock_history(symbol, days=days)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
    fig = plot_candlestick_with_indicators(df, symbol)
    return json.loads(fig.to_json())
