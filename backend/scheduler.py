import json
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

IST = pytz.timezone("Asia/Kolkata")
_scheduler = BackgroundScheduler(timezone=IST)

_ALERTS_PATH = Path(__file__).parent.parent / "config" / "alerts.json"


def _load_alerts() -> dict:
    if _ALERTS_PATH.exists():
        return json.loads(_ALERTS_PATH.read_text())
    return {"email": "", "alerts": []}


def _save_alerts(data: dict):
    _ALERTS_PATH.write_text(json.dumps(data, indent=2))


def _run_opening_report():
    data = _load_alerts()
    email = data.get("email", "")
    if not email:
        return
    try:
        from backend.email_service import send_opening_report
        send_opening_report(email)
        print("[scheduler] Opening report sent.")
    except Exception as e:
        print(f"[scheduler] Opening report failed: {e}")


def _run_closing_report():
    data = _load_alerts()
    email = data.get("email", "")
    if not email:
        return
    try:
        from backend.email_service import send_closing_report
        send_closing_report(email)
        print("[scheduler] Closing report sent.")
    except Exception as e:
        print(f"[scheduler] Closing report failed: {e}")


def _check_price_alerts():
    data = _load_alerts()
    email = data.get("email", "")
    alerts = data.get("alerts", [])
    if not email or not alerts:
        return

    changed = False
    try:
        from data.fetcher import fetch_stock_history
        from data.processor import get_latest_stats
        from backend.email_service import send_price_alert

        for alert in alerts:
            symbol = alert.get("symbol", "")
            above = alert.get("above")
            below = alert.get("below")

            df = fetch_stock_history(symbol)
            if df is None or df.empty:
                continue
            stats = get_latest_stats(df)
            price = stats.get("price", 0)
            if not price:
                continue

            if above is not None and price >= above and not alert.get("triggered_above"):
                send_price_alert(email, symbol, price, above, "above")
                alert["triggered_above"] = True
                changed = True
                print(f"[scheduler] Alert: {symbol} above {above} at {price}")

            if below is not None and price <= below and not alert.get("triggered_below"):
                send_price_alert(email, symbol, price, below, "below")
                alert["triggered_below"] = True
                changed = True
                print(f"[scheduler] Alert: {symbol} below {below} at {price}")

    except Exception as e:
        print(f"[scheduler] Alert check failed: {e}")

    if changed:
        _save_alerts(data)


def _reset_alert_triggers():
    """Reset triggered flags every day at midnight so alerts can fire again."""
    data = _load_alerts()
    for alert in data.get("alerts", []):
        alert["triggered_above"] = False
        alert["triggered_below"] = False
    _save_alerts(data)


def start_scheduler():
    # Market opening report — weekdays 9:15am IST
    _scheduler.add_job(_run_opening_report, CronTrigger(hour=9, minute=15, day_of_week="mon-fri"), id="opening_report")
    # Market closing report — weekdays 3:35pm IST
    _scheduler.add_job(_run_closing_report, CronTrigger(hour=15, minute=35, day_of_week="mon-fri"), id="closing_report")
    # Price alert checker — every minute, weekdays during market hours
    _scheduler.add_job(_check_price_alerts, CronTrigger(minute="*/1", hour="9-15", day_of_week="mon-fri"), id="alert_checker")
    # Reset alert triggers daily at midnight
    _scheduler.add_job(_reset_alert_triggers, CronTrigger(hour=0, minute=0), id="reset_triggers")
    _scheduler.start()
    print("[scheduler] Started.")


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("[scheduler] Stopped.")
