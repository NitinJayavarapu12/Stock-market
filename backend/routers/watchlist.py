import os
import json
import requests
from pathlib import Path
from fastapi import APIRouter, HTTPException
from data.fetcher import fetch_stock_history
from data.processor import get_latest_stats

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY", "")
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID", "")

_LOCAL_PATH = Path(__file__).parent.parent.parent / "config" / "watchlist.json"


def _load() -> list:
    if JSONBIN_API_KEY and JSONBIN_BIN_ID:
        try:
            resp = requests.get(
                f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest",
                headers={"X-Master-Key": JSONBIN_API_KEY},
                timeout=5,
            )
            resp.raise_for_status()
            return resp.json().get("record", [])
        except Exception:
            pass
    if _LOCAL_PATH.exists():
        return json.loads(_LOCAL_PATH.read_text())
    return []


def _save(symbols: list):
    if JSONBIN_API_KEY and JSONBIN_BIN_ID:
        try:
            requests.put(
                f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}",
                headers={"X-Master-Key": JSONBIN_API_KEY, "Content-Type": "application/json"},
                json=symbols,
                timeout=5,
            )
            return
        except Exception:
            pass
    _LOCAL_PATH.write_text(json.dumps(symbols, indent=2))


def _normalize(symbol: str) -> str:
    sym = symbol.upper().strip()
    if "." not in sym:
        sym += ".NS"
    return sym


@router.get("")
def get_watchlist():
    symbols = _load()
    result = []
    for sym in symbols:
        df = fetch_stock_history(sym)
        if df is not None and not df.empty:
            stats = get_latest_stats(df)
            result.append({"symbol": sym, **stats})
        else:
            result.append({"symbol": sym})
    return result


@router.post("/{symbol}")
def add_to_watchlist(symbol: str):
    sym = _normalize(symbol)
    symbols = _load()
    if sym not in symbols:
        symbols.append(sym)
        _save(symbols)
    return {"symbols": symbols}


@router.delete("/{symbol}")
def remove_from_watchlist(symbol: str):
    sym = _normalize(symbol)
    symbols = [s for s in _load() if s != sym]
    _save(symbols)
    return {"symbols": symbols}
