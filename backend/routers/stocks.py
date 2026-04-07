import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from data.fetcher import fetch_stock_history, search_stocks, fetch_fundamentals
from data.processor import get_latest_stats
from models.indicators import get_indicator_summary
from ui.charts import plot_candlestick_with_indicators
from backend.serializers import df_to_records
from config.settings import HISTORY_DAYS_DEFAULT, NIFTY_50_SYMBOLS

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


def _label_roe_roce(value: Optional[float]) -> str:
    if value is None:
        return "Not available"
    if value >= 20:
        return "Excellent"
    if value >= 15:
        return "Good"
    if value >= 10:
        return "Fair"
    return "Weak"


def _label_peg(value: Optional[float]) -> str:
    if value is None:
        return "Not available"
    if value < 0.5:
        return "Potentially Cheap"
    if value < 1:
        return "Fairly Valued"
    if value < 2:
        return "Slightly Expensive"
    return "Overvalued"


def _color_roe_roce(value: Optional[float]) -> str:
    if value is None:
        return "gray"
    if value >= 15:
        return "green"
    if value >= 10:
        return "yellow"
    return "red"


def _color_peg(value: Optional[float]) -> str:
    if value is None:
        return "gray"
    if value < 1:
        return "green"
    if value < 2:
        return "yellow"
    return "red"


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


@router.get("/{symbol}/fundamentals")
def stock_fundamentals(symbol: str):
    raw = fetch_fundamentals(symbol)
    return {
        "roce": {
            "value": raw["roce"],
            "label": _label_roe_roce(raw["roce"]),
            "color": _color_roe_roce(raw["roce"]),
            "unit": "%",
        },
        "roe": {
            "value": raw["roe"],
            "label": _label_roe_roce(raw["roe"]),
            "color": _color_roe_roce(raw["roe"]),
            "unit": "%",
        },
        "peg": {
            "value": raw["peg"],
            "label": _label_peg(raw["peg"]),
            "color": _color_peg(raw["peg"]),
            "unit": "x",
        },
    }


@router.get("/{symbol}/chart-json")
def stock_chart_json(symbol: str, days: int = HISTORY_DAYS_DEFAULT):
    df = fetch_stock_history(symbol, days=days)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
    fig = plot_candlestick_with_indicators(df, symbol)
    return json.loads(fig.to_json())
