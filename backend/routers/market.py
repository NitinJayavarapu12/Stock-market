import json
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from data.fetcher import fetch_index_data, fetch_movers, get_market_status_label
from ai.gemini_client import generate_market_overview
from config.settings import INDICES
from ui.charts import plot_movers_table, plot_sparkline
from data.fetcher import fetch_stock_history

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/status")
def market_status():
    return {"label": get_market_status_label()}


@router.get("/indices")
def market_indices():
    result = {}
    for name, symbol in INDICES.items():
        data = fetch_index_data(symbol)
        if data:
            result[name] = data
    return result


@router.get("/movers")
def market_movers():
    return fetch_movers()


@router.get("/movers/chart-json")
def movers_chart_json():
    movers = fetch_movers()
    gainers_fig = plot_movers_table(movers.get("gainers", []), "Gainers")
    losers_fig = plot_movers_table(movers.get("losers", []), "Losers")
    return {
        "gainers": json.loads(gainers_fig.to_json()),
        "losers": json.loads(losers_fig.to_json()),
    }


@router.get("/overview")
def market_overview():
    index_data = {}
    for name, symbol in INDICES.items():
        data = fetch_index_data(symbol)
        if data:
            index_data[name] = data
    movers = fetch_movers()
    text = generate_market_overview(index_data, movers)
    return {"text": text}
