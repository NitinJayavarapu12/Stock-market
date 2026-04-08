import io
import csv
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from backend.auth import get_user_id
from backend.supabase_client import get_supabase
from data.fetcher import fetch_stock_history
from data.processor import get_latest_stats

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class HoldingIn(BaseModel):
    symbol: str
    company: str = ""
    quantity: float
    avg_buy_price: float


def _normalize(symbol: str) -> str:
    sym = symbol.upper().strip()
    if "." not in sym:
        sym += ".NS"
    return sym


def _enrich_holdings(holdings: list) -> list:
    """Add current price and P&L to each holding."""
    result = []
    for h in holdings:
        symbol = h["symbol"]
        df = fetch_stock_history(symbol)
        if df is not None and not df.empty:
            stats = get_latest_stats(df)
            current_price = stats.get("price", 0)
        else:
            current_price = 0

        qty = h["quantity"]
        avg_price = h["avg_buy_price"]
        invested = round(qty * avg_price, 2)
        current_value = round(qty * current_price, 2)
        pnl = round(current_value - invested, 2)
        pnl_pct = round((pnl / invested * 100), 2) if invested else 0

        result.append({
            **h,
            "current_price": current_price,
            "invested": invested,
            "current_value": current_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        })
    return result


@router.get("")
def get_portfolio(user_id: str = Depends(get_user_id)):
    sb = get_supabase()
    resp = sb.table("portfolio_holdings").select("*").eq("user_id", user_id).execute()
    holdings = resp.data or []
    enriched = _enrich_holdings(holdings)

    total_invested = round(sum(h["invested"] for h in enriched), 2)
    total_value = round(sum(h["current_value"] for h in enriched), 2)
    total_pnl = round(total_value - total_invested, 2)
    total_pnl_pct = round((total_pnl / total_invested * 100), 2) if total_invested else 0

    return {
        "holdings": enriched,
        "summary": {
            "total_invested": total_invested,
            "total_value": total_value,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "count": len(enriched),
        },
    }


@router.post("")
def add_holding(body: HoldingIn, user_id: str = Depends(get_user_id)):
    sb = get_supabase()
    symbol = _normalize(body.symbol)
    data = {
        "user_id": user_id,
        "symbol": symbol,
        "company": body.company or symbol.replace(".NS", "").replace(".BO", ""),
        "quantity": body.quantity,
        "avg_buy_price": body.avg_buy_price,
    }
    # Upsert — if same symbol exists, update it
    sb.table("portfolio_holdings").upsert(data, on_conflict="user_id,symbol").execute()
    return {"ok": True}


@router.put("/{symbol}")
def update_holding(symbol: str, body: HoldingIn, user_id: str = Depends(get_user_id)):
    sb = get_supabase()
    sym = _normalize(symbol)
    sb.table("portfolio_holdings").update({
        "quantity": body.quantity,
        "avg_buy_price": body.avg_buy_price,
    }).eq("user_id", user_id).eq("symbol", sym).execute()
    return {"ok": True}


@router.delete("/{symbol}")
def delete_holding(symbol: str, user_id: str = Depends(get_user_id)):
    sb = get_supabase()
    sym = _normalize(symbol)
    sb.table("portfolio_holdings").delete().eq("user_id", user_id).eq("symbol", sym).execute()
    return {"ok": True}


@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...), user_id: str = Depends(get_user_id)):
    """
    Parse broker CSV and bulk-upsert holdings.
    Supports: Zerodha, Groww, Upstox, and generic CSV.
    """
    content = await file.read()
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        raise HTTPException(status_code=400, detail="CSV is empty or unreadable")

    headers = [h.strip().lower() for h in rows[0].keys()]

    def _find_col(candidates: list) -> Optional[str]:
        for c in candidates:
            for h in rows[0].keys():
                if c in h.strip().lower():
                    return h
        return None

    symbol_col = _find_col(["tradingsymbol", "symbol", "ticker", "scrip", "stock"])
    qty_col = _find_col(["quantity", "qty", "shares"])
    price_col = _find_col(["average", "avg", "buy price", "purchase price", "cost price"])

    if not symbol_col or not qty_col or not price_col:
        raise HTTPException(
            status_code=400,
            detail=f"Could not detect required columns. Found: {list(rows[0].keys())}. "
                   "Need columns for: symbol, quantity, average buy price."
        )

    sb = get_supabase()
    upserted = 0
    errors = []

    for row in rows:
        try:
            raw_sym = str(row[symbol_col]).strip().upper()
            if not raw_sym or raw_sym == "SYMBOL":
                continue
            symbol = _normalize(raw_sym)
            qty = float(str(row[qty_col]).replace(",", "").strip())
            price = float(str(row[price_col]).replace(",", "").replace("₹", "").strip())
            if qty <= 0 or price <= 0:
                continue

            sb.table("portfolio_holdings").upsert({
                "user_id": user_id,
                "symbol": symbol,
                "company": symbol.replace(".NS", "").replace(".BO", ""),
                "quantity": qty,
                "avg_buy_price": price,
            }, on_conflict="user_id,symbol").execute()
            upserted += 1
        except Exception as e:
            errors.append(str(e))

    return {"imported": upserted, "errors": errors}
