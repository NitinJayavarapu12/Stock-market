from fastapi import APIRouter, Depends
from backend.auth import get_user_id
from backend.supabase_client import get_supabase
from data.fetcher import fetch_stock_history
from data.processor import get_latest_stats

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


def _normalize(symbol: str) -> str:
    sym = symbol.upper().strip()
    if "." not in sym:
        sym += ".NS"
    return sym


@router.get("")
def get_watchlist(user_id: str = Depends(get_user_id)):
    sb = get_supabase()
    resp = sb.table("watchlist").select("*").eq("user_id", user_id).execute()
    items = resp.data or []

    result = []
    for item in items:
        sym = item["symbol"]
        df = fetch_stock_history(sym)
        if df is not None and not df.empty:
            stats = get_latest_stats(df)
            result.append({"symbol": sym, "company": item.get("company", ""), **stats})
        else:
            result.append({"symbol": sym, "company": item.get("company", "")})
    return result


@router.post("/{symbol}")
def add_to_watchlist(symbol: str, user_id: str = Depends(get_user_id)):
    sb = get_supabase()
    sym = _normalize(symbol)
    company = sym.replace(".NS", "").replace(".BO", "")
    sb.table("watchlist").upsert(
        {"user_id": user_id, "symbol": sym, "company": company},
        on_conflict="user_id,symbol"
    ).execute()
    return {"ok": True}


@router.delete("/{symbol}")
def remove_from_watchlist(symbol: str, user_id: str = Depends(get_user_id)):
    sb = get_supabase()
    sym = _normalize(symbol)
    sb.table("watchlist").delete().eq("user_id", user_id).eq("symbol", sym).execute()
    return {"ok": True}
