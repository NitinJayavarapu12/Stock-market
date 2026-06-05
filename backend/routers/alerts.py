from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from backend.auth import get_user_id
from backend.supabase_client import get_supabase

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

PREF_COLS = "alert_email,notif_daily_reports,notif_price_alerts,notif_market_anomaly,notif_watchlist_spikes,notif_portfolio_moves,notif_recommendations"


class AlertConfig(BaseModel):
    email: str


class AlertThreshold(BaseModel):
    above: Optional[float] = None
    below: Optional[float] = None


class NotifPreferences(BaseModel):
    notif_daily_reports: Optional[bool] = None
    notif_price_alerts: Optional[bool] = None
    notif_market_anomaly: Optional[bool] = None
    notif_watchlist_spikes: Optional[bool] = None
    notif_portfolio_moves: Optional[bool] = None
    notif_recommendations: Optional[bool] = None


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


def _get_user_prefs(user_id: str) -> dict:
    sb = get_supabase()
    res = sb.table("user_preferences").select(PREF_COLS).eq("user_id", user_id).execute()
    rows = res.data or []
    if not rows:
        return {"alert_email": "", "notif_daily_reports": True, "notif_price_alerts": True,
                "notif_market_anomaly": True, "notif_watchlist_spikes": True,
                "notif_portfolio_moves": True, "notif_recommendations": True}
    r = rows[0]
    return {
        "alert_email": r.get("alert_email", ""),
        "notif_daily_reports": r.get("notif_daily_reports") is not False,
        "notif_price_alerts": r.get("notif_price_alerts") is not False,
        "notif_market_anomaly": r.get("notif_market_anomaly") is not False,
        "notif_watchlist_spikes": r.get("notif_watchlist_spikes") is not False,
        "notif_portfolio_moves": r.get("notif_portfolio_moves") is not False,
        "notif_recommendations": r.get("notif_recommendations") is not False,
    }


@router.get("")
def get_alerts(user_id: str = Depends(get_user_id)):
    prefs = _get_user_prefs(user_id)
    alerts = _get_user_alerts(user_id)
    return {
        "email": prefs.pop("alert_email"),
        "alerts": alerts,
        "preferences": prefs,
    }


@router.put("/config")
def set_email(body: AlertConfig, user_id: str = Depends(get_user_id)):
    sb = get_supabase()
    sb.table("user_preferences").upsert(
        {"user_id": user_id, "alert_email": body.email.strip()},
        on_conflict="user_id",
    ).execute()
    return {"email": body.email.strip()}


@router.put("/preferences")
def set_preferences(body: NotifPreferences, user_id: str = Depends(get_user_id)):
    sb = get_supabase()
    update = {k: v for k, v in body.model_dump().items() if v is not None}
    if update:
        update["user_id"] = user_id
        sb.table("user_preferences").upsert(update, on_conflict="user_id").execute()
    prefs = _get_user_prefs(user_id)
    prefs.pop("alert_email", None)
    return prefs


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
