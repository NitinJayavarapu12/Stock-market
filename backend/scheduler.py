from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

IST = pytz.timezone("Asia/Kolkata")
_scheduler = BackgroundScheduler(timezone=IST)


def _get_all_users_with_email() -> list[dict]:
    """Return list of {user_id, alert_email} for users who have an alert email set."""
    try:
        from backend.supabase_client import get_supabase
        sb = get_supabase()
        res = sb.table("user_preferences").select("user_id,alert_email").neq("alert_email", "").neq("alert_email", None).execute()
        return res.data or []
    except Exception as e:
        print(f"[scheduler] Failed to fetch users: {e}")
        return []


def _get_user_watchlist(user_id: str) -> list[str]:
    try:
        from backend.supabase_client import get_supabase
        sb = get_supabase()
        res = sb.table("watchlist").select("symbol").eq("user_id", user_id).execute()
        return [r["symbol"] for r in (res.data or [])]
    except Exception:
        return []


def _get_user_portfolio(user_id: str) -> list[dict]:
    try:
        from backend.supabase_client import get_supabase
        sb = get_supabase()
        res = sb.table("portfolio_holdings").select("*").eq("user_id", user_id).execute()
        return res.data or []
    except Exception:
        return []


def _get_user_alerts(user_id: str) -> list[dict]:
    try:
        from backend.supabase_client import get_supabase
        sb = get_supabase()
        res = sb.table("price_alerts").select("*").eq("user_id", user_id).execute()
        return res.data or []
    except Exception:
        return []


def _save_alert_triggered(alert_id: str, field: str):
    try:
        from backend.supabase_client import get_supabase
        sb = get_supabase()
        sb.table("price_alerts").update({field: True}).eq("id", alert_id).execute()
    except Exception as e:
        print(f"[scheduler] Failed to save alert trigger: {e}")


def _reset_all_alert_triggers():
    try:
        from backend.supabase_client import get_supabase
        sb = get_supabase()
        sb.table("price_alerts").update({"triggered_above": False, "triggered_below": False}).neq("id", "").execute()
        print("[scheduler] Alert triggers reset.")
    except Exception as e:
        print(f"[scheduler] Failed to reset triggers: {e}")


def _run_opening_report():
    users = _get_all_users_with_email()
    if not users:
        return
    try:
        from backend.email_service import send_opening_report
        for u in users:
            user_id = u["user_id"]
            email = u["alert_email"]
            watchlist = _get_user_watchlist(user_id)
            portfolio = _get_user_portfolio(user_id)
            send_opening_report(email, watchlist, portfolio)
            print(f"[scheduler] Opening report sent to {email}")
    except Exception as e:
        print(f"[scheduler] Opening report failed: {e}")


def _run_closing_report():
    users = _get_all_users_with_email()
    if not users:
        return
    try:
        from backend.email_service import send_closing_report
        for u in users:
            user_id = u["user_id"]
            email = u["alert_email"]
            watchlist = _get_user_watchlist(user_id)
            portfolio = _get_user_portfolio(user_id)
            send_closing_report(email, watchlist, portfolio)
            print(f"[scheduler] Closing report sent to {email}")
    except Exception as e:
        print(f"[scheduler] Closing report failed: {e}")


def _check_price_alerts():
    users = _get_all_users_with_email()
    if not users:
        return
    try:
        from data.fetcher import fetch_stock_history
        from data.processor import get_latest_stats
        from backend.email_service import send_price_alert

        for u in users:
            user_id = u["user_id"]
            email = u["alert_email"]
            alerts = _get_user_alerts(user_id)

            for alert in alerts:
                symbol = alert.get("symbol", "")
                above = alert.get("alert_above")
                below = alert.get("alert_below")
                alert_id = alert.get("id")

                df = fetch_stock_history(symbol)
                if df is None or df.empty:
                    continue
                stats = get_latest_stats(df)
                price = stats.get("price", 0)
                if not price:
                    continue

                if above is not None and price >= above and not alert.get("triggered_above"):
                    send_price_alert(email, symbol, price, above, "above")
                    _save_alert_triggered(alert_id, "triggered_above")
                    print(f"[scheduler] Alert: {symbol} above {above} at {price} → {email}")

                if below is not None and price <= below and not alert.get("triggered_below"):
                    send_price_alert(email, symbol, price, below, "below")
                    _save_alert_triggered(alert_id, "triggered_below")
                    print(f"[scheduler] Alert: {symbol} below {below} at {price} → {email}")

    except Exception as e:
        print(f"[scheduler] Alert check failed: {e}")


def start_scheduler():
    _scheduler.add_job(_run_opening_report, CronTrigger(hour=9, minute=15, day_of_week="mon-fri"), id="opening_report")
    _scheduler.add_job(_run_closing_report, CronTrigger(hour=15, minute=35, day_of_week="mon-fri"), id="closing_report")
    _scheduler.add_job(_check_price_alerts, CronTrigger(minute="*/1", hour="9-15", day_of_week="mon-fri"), id="alert_checker")
    _scheduler.add_job(_reset_all_alert_triggers, CronTrigger(hour=0, minute=0), id="reset_triggers")
    _scheduler.start()
    print("[scheduler] Started.")


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("[scheduler] Stopped.")
