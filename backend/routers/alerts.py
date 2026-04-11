from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from backend.auth import get_user_id
from backend.supabase_client import get_supabase

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class AlertConfig(BaseModel):
    email: str


class AlertThreshold(BaseModel):
    above: Optional[float] = None
    below: Optional[float] = None


def _get_user_alerts(user_id: str) -> list:
    sb = get_supabase()
    res = sb.table("price_alerts").select("*").eq("user_id", user_id).execute()
    rows = res.data or []
    return [
        {
            "symbol": r["symbol"],
            "above": r.get("alert_above"),
            "below": r.get("alert_below"),
        }
        for r in rows
    ]


def _get_user_email(user_id: str) -> str:
    sb = get_supabase()
    res = sb.table("user_preferences").select("alert_email").eq("user_id", user_id).execute()
    rows = res.data or []
    return rows[0]["alert_email"] if rows else ""


@router.get("")
def get_alerts(user_id: str = Depends(get_user_id)):
    email = _get_user_email(user_id)
    alerts = _get_user_alerts(user_id)
    return {"email": email, "alerts": alerts}


@router.put("/config")
def set_email(body: AlertConfig, user_id: str = Depends(get_user_id)):
    sb = get_supabase()
    sb.table("user_preferences").upsert(
        {"user_id": user_id, "alert_email": body.email.strip()},
        on_conflict="user_id",
    ).execute()
    return {"email": body.email.strip()}


@router.post("/{symbol}")
def set_alert(symbol: str, body: AlertThreshold, user_id: str = Depends(get_user_id)):
    sym = symbol.upper().strip()
    sb = get_supabase()
    sb.table("price_alerts").upsert(
        {
            "user_id": user_id,
            "symbol": sym,
            "alert_above": body.above,
            "alert_below": body.below,
            "triggered_above": False,
            "triggered_below": False,
        },
        on_conflict="user_id,symbol",
    ).execute()
    alerts = _get_user_alerts(user_id)
    email = _get_user_email(user_id)
    return {"email": email, "alerts": alerts}


@router.delete("/{symbol}")
def remove_alert(symbol: str, user_id: str = Depends(get_user_id)):
    sym = symbol.upper().strip()
    sb = get_supabase()
    sb.table("price_alerts").delete().eq("user_id", user_id).eq("symbol", sym).execute()
    alerts = _get_user_alerts(user_id)
    email = _get_user_email(user_id)
    return {"email": email, "alerts": alerts}
