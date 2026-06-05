from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date
import pytz

IST = pytz.timezone("Asia/Kolkata")
_scheduler = BackgroundScheduler(timezone=IST)

# In-memory dedup: tracks which (symbol, alert_type) already fired today
# Resets naturally when Render restarts (daily); also reset explicitly at midnight
_fired_today: set = set()


def _dedup_key(symbol: str, alert_type: str) -> str:
    return f"{date.today().isoformat()}:{symbol}:{alert_type}"


def _already_fired(symbol: str, alert_type: str) -> bool:
    return _dedup_key(symbol, alert_type) in _fired_today


def _mark_fired(symbol: str, alert_type: str):
    _fired_today.add(_dedup_key(symbol, alert_type))


def _reset_fired():
    _fired_today.clear()
    print("[scheduler] Daily dedup reset.")


# ── Supabase helpers ──────────────────────────────────────────────────────────

_PREF_COLS = (
    "user_id,alert_email,"
    "notif_daily_reports,notif_price_alerts,notif_market_anomaly,"
    "notif_watchlist_spikes,notif_portfolio_moves,notif_recommendations"
)


def _get_all_users_with_email() -> list[dict]:
    try:
        from backend.supabase_client import get_supabase
        sb = get_supabase()
        res = (
            sb.table("user_preferences")
            .select(_PREF_COLS)
            .neq("alert_email", "")
            .neq("alert_email", None)
            .execute()
        )
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


# ── Scheduled jobs ────────────────────────────────────────────────────────────

def _run_opening_report():
    users = _get_all_users_with_email()
    if not users:
        return
    try:
        from backend.email_service import send_opening_report
        for u in users:
            if u.get("notif_daily_reports") is False:
                continue
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
            if u.get("notif_daily_reports") is False:
                continue
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
            if u.get("notif_price_alerts") is False:
                continue
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


def _check_market_anomalies():
    """
    Check NIFTY 50 and SENSEX for statistically unusual moves.
    Uses Z-score against 20-day rolling volatility (|Z| > 2 = anomaly).
    Fires once per index per day. AI commentary generated per alert.
    """
    from config.settings import INDICES
    from data.fetcher import fetch_volatility_stats
    from backend.email_service import send_market_anomaly_alert
    from ai.gemini_client import generate_alert_commentary

    users = _get_all_users_with_email()
    if not users:
        return

    Z_THRESHOLD = 2.0

    for index_name, index_symbol in INDICES.items():
        if _already_fired(index_symbol, "market_anomaly"):
            continue

        stats = fetch_volatility_stats(index_symbol)
        if stats is None:
            continue

        z = stats["z_score"]
        if abs(z) < Z_THRESHOLD:
            continue

        direction = "surged" if z > 0 else "crashed"
        alert_type = f"Market {direction.title()} — {index_name}"

        commentary = generate_alert_commentary(
            symbol=index_name,
            alert_type=alert_type,
            z_score=z,
            today_return_pct=stats["today_return_pct"],
            current_price=stats["current_price"],
            mean_return_pct=stats["mean_return_pct"],
        )

        _mark_fired(index_symbol, "market_anomaly")

        for u in users:
            if u.get("notif_market_anomaly") is False:
                continue
            try:
                send_market_anomaly_alert(
                    to=u["alert_email"],
                    index_name=index_name,
                    stats=stats,
                    commentary=commentary,
                )
                print(f"[scheduler] Market anomaly alert ({index_name} Z={z:+.2f}) → {u['alert_email']}")
            except Exception as e:
                print(f"[scheduler] Market anomaly email failed: {e}")


def _check_watchlist_spikes():
    """
    For each user's watchlist, check if any stock has moved more than
    2 standard deviations from its own 20-day rolling volatility baseline.
    Fires once per stock per user per day.
    """
    from data.fetcher import fetch_volatility_stats
    from backend.email_service import send_watchlist_spike_alert
    from ai.gemini_client import generate_alert_commentary

    users = _get_all_users_with_email()
    if not users:
        return

    Z_THRESHOLD = 2.0

    for u in users:
        if u.get("notif_watchlist_spikes") is False:
            continue
        user_id = u["user_id"]
        email = u["alert_email"]
        symbols = _get_user_watchlist(user_id)

        for symbol in symbols:
            dedup_key_user = f"{user_id}:{symbol}"
            if _already_fired(dedup_key_user, "watchlist_spike"):
                continue

            stats = fetch_volatility_stats(symbol)
            if stats is None:
                continue

            z = stats["z_score"]
            if abs(z) < Z_THRESHOLD:
                continue

            direction = "surged" if z > 0 else "dropped"
            alert_type = f"Watchlist Spike — {symbol.replace('.NS','').replace('.BO','')} {direction}"

            commentary = generate_alert_commentary(
                symbol=symbol.replace(".NS", "").replace(".BO", ""),
                alert_type=alert_type,
                z_score=z,
                today_return_pct=stats["today_return_pct"],
                current_price=stats["current_price"],
                mean_return_pct=stats["mean_return_pct"],
            )

            _mark_fired(dedup_key_user, "watchlist_spike")

            try:
                send_watchlist_spike_alert(
                    to=email,
                    symbol=symbol,
                    stats=stats,
                    commentary=commentary,
                )
                print(f"[scheduler] Watchlist spike ({symbol} Z={z:+.2f}) → {email}")
            except Exception as e:
                print(f"[scheduler] Watchlist spike email failed: {e}")


def _check_portfolio_moves():
    """
    For each user's portfolio holdings, check if any holding has moved >= 3% today.
    Fires once per (user, symbol, direction) per day.
    """
    THRESHOLD = 3.0

    from data.fetcher import fetch_stock_history
    from data.processor import get_latest_stats
    from backend.email_service import send_portfolio_move_alert

    users = _get_all_users_with_email()
    if not users:
        return

    for u in users:
        if u.get("notif_portfolio_moves") is False:
            continue
        user_id = u["user_id"]
        email = u["alert_email"]
        holdings = _get_user_portfolio(user_id)
        if not holdings:
            continue

        for holding in holdings:
            symbol = holding.get("symbol", "")
            if not symbol:
                continue
            company = holding.get("company", "") or symbol.replace(".NS", "").replace(".BO", "")

            df = fetch_stock_history(symbol)
            if df is None or df.empty:
                continue

            stats = get_latest_stats(df)
            day_change_pct = stats.get("day_change_pct")
            if day_change_pct is None or abs(day_change_pct) < THRESHOLD:
                continue

            direction = "up" if day_change_pct > 0 else "down"
            dedup_key = f"{user_id}:{symbol}"
            if _already_fired(dedup_key, f"portfolio_spike_{direction}"):
                continue

            _mark_fired(dedup_key, f"portfolio_spike_{direction}")
            try:
                send_portfolio_move_alert(
                    to=email,
                    symbol=symbol,
                    company=company,
                    direction=direction,
                    stats=stats,
                    holding={"quantity": holding.get("quantity", 0), "avg_buy_price": holding.get("avg_buy_price", 0)},
                )
                print(f"[scheduler] Portfolio move ({symbol} {day_change_pct:+.2f}%) → {email}")
            except Exception as e:
                print(f"[scheduler] Portfolio move email failed for {symbol}: {e}")


def _run_recommendation_scan():
    """
    Daily buy opportunity scan: NIFTY 50 + user watchlist, technical screener,
    Prophet upside on top 5 candidates, Gemini AI commentary.
    Runs once at 10:00 AM IST Mon-Fri.
    """
    from config.settings import NIFTY_50_SYMBOLS, HISTORY_DAYS_PREDICTION
    from data.fetcher import fetch_stock_history
    from data.screener import screen_buy_opportunities
    from models.predictor import run_prophet_prediction
    from ai.gemini_client import generate_recommendation_commentary
    from backend.email_service import send_recommendation_email

    FINAL_THRESHOLD = 60
    TOP_N = 5

    users = _get_all_users_with_email()
    if not users:
        return

    for u in users:
        if u.get("notif_recommendations") is False:
            continue
        user_id = u["user_id"]
        email = u["alert_email"]

        if _already_fired(user_id, "recommendation_scan"):
            continue

        watchlist = _get_user_watchlist(user_id)
        universe = list(dict.fromkeys(NIFTY_50_SYMBOLS + watchlist))

        try:
            candidates = screen_buy_opportunities(universe)
        except Exception as e:
            print(f"[scheduler] Screener failed for {email}: {e}")
            _mark_fired(user_id, "recommendation_scan")
            continue

        if not candidates:
            print(f"[scheduler] No screener candidates for {email}.")
            _mark_fired(user_id, "recommendation_scan")
            continue

        final_candidates = []
        for candidate in candidates[:TOP_N]:
            symbol = candidate["symbol"]
            prophet_upside_pct = 0.0
            prophet_score = 0

            try:
                df_long = fetch_stock_history(symbol, days=HISTORY_DAYS_PREDICTION)
                if df_long is not None and len(df_long) >= 60:
                    result = run_prophet_prediction(df_long, horizon_days=30)
                    upside = result.get("percent_change")
                    if upside is not None:
                        prophet_upside_pct = float(upside)
                        prophet_score = 20 if prophet_upside_pct > 10 else (10 if prophet_upside_pct > 5 else 0)
            except Exception as e:
                print(f"[scheduler] Prophet failed for {symbol}: {e}")

            final_score = candidate["composite_score"] + prophet_score
            if final_score < FINAL_THRESHOLD:
                continue

            ai_commentary = ""
            try:
                ai_commentary = generate_recommendation_commentary(
                    symbol=symbol,
                    company=candidate["company"],
                    stats=candidate["stats"],
                    indicators=candidate["indicators"],
                    prophet_upside_pct=prophet_upside_pct,
                )
            except Exception as e:
                print(f"[scheduler] AI commentary failed for {symbol}: {e}")

            final_candidates.append({
                "symbol": symbol,
                "company": candidate["company"],
                "price": candidate["price"],
                "day_change_pct": candidate["day_change_pct"],
                "rsi": candidate["rsi"],
                "macd_signal": candidate["macd_signal"],
                "bb_position": candidate["bb_position"],
                "prophet_upside_pct": round(prophet_upside_pct, 2),
                "composite_score": round(final_score, 1),
                "ai_commentary": ai_commentary or f"{candidate['company']} shows technical buy signals with {prophet_upside_pct:+.1f}% model upside.",
            })

        _mark_fired(user_id, "recommendation_scan")

        if not final_candidates:
            print(f"[scheduler] No candidates passed final threshold for {email}.")
            continue

        final_candidates.sort(key=lambda x: x["composite_score"], reverse=True)
        try:
            send_recommendation_email(to=email, recommendations=final_candidates)
            print(f"[scheduler] Recommendations: {len(final_candidates)} stock(s) → {email}")
        except Exception as e:
            print(f"[scheduler] Recommendation email failed for {email}: {e}")


def start_scheduler():
    _scheduler.add_job(_run_opening_report, CronTrigger(hour=9, minute=15, day_of_week="mon-fri"), id="opening_report")
    _scheduler.add_job(_run_closing_report, CronTrigger(hour=15, minute=35, day_of_week="mon-fri"), id="closing_report")
    _scheduler.add_job(_check_price_alerts, CronTrigger(minute="*/1", hour="9-15", day_of_week="mon-fri"), id="alert_checker")
    _scheduler.add_job(_check_market_anomalies, CronTrigger(minute="*/5", hour="9-15", day_of_week="mon-fri"), id="market_anomaly")
    _scheduler.add_job(_check_watchlist_spikes, CronTrigger(minute="*/5", hour="9-15", day_of_week="mon-fri"), id="watchlist_spikes")
    _scheduler.add_job(_check_portfolio_moves, CronTrigger(minute="*/5", hour="9-15", day_of_week="mon-fri"), id="portfolio_moves")
    _scheduler.add_job(_run_recommendation_scan, CronTrigger(hour=10, minute=0, day_of_week="mon-fri"), id="recommendation_scan")
    _scheduler.add_job(_reset_all_alert_triggers, CronTrigger(hour=0, minute=0), id="reset_triggers")
    _scheduler.add_job(_reset_fired, CronTrigger(hour=0, minute=1), id="reset_fired")
    _scheduler.start()
    print("[scheduler] Started.")


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("[scheduler] Stopped.")
