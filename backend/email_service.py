import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")


def _send(to: str, subject: str, html: str):
    gmail_user = os.getenv("GMAIL_USER", "")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD", "")
    if not gmail_user or not gmail_password or not to:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Stock Insights <{gmail_user}>"
        msg["To"] = to
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, to, msg.as_string())
        return True
    except Exception as e:
        print(f"[email] Failed to send: {e}")
        return False


def _card(title: str, value: str, sub: str = "", color: str = "#ffffff") -> str:
    return f"""
    <div style="background:#1e2130;border:1px solid #334155;border-radius:12px;padding:16px;min-width:140px;display:inline-block;margin:6px;vertical-align:top;">
      <p style="color:#94a3b8;font-size:12px;margin:0 0 4px">{title}</p>
      <p style="color:{color};font-size:22px;font-weight:700;margin:0">{value}</p>
      {'<p style="color:#94a3b8;font-size:12px;margin:4px 0 0">' + sub + '</p>' if sub else ''}
    </div>"""


def _base_template(title: str, subtitle: str, body: str) -> str:
    return f"""
<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="background:#0f1117;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:24px;color:#e2e8f0">
  <div style="max-width:600px;margin:0 auto">
    <div style="margin-bottom:24px">
      <h1 style="color:#ffffff;font-size:24px;margin:0">📈 Stock Insights</h1>
      <p style="color:#64748b;font-size:13px;margin:4px 0 0">{subtitle}</p>
    </div>
    <div style="background:#12141e;border-radius:16px;padding:24px;border:1px solid #1e293b">
      <h2 style="color:#ffffff;font-size:18px;margin:0 0 20px">{title}</h2>
      {body}
    </div>
    <p style="color:#475569;font-size:11px;margin:16px 0 0;text-align:center">
      ⚠️ For educational purposes only. Not financial advice.
    </p>
  </div>
</body></html>"""


def _watchlist_section(symbols: list[str]) -> str:
    """Build watchlist HTML rows for email reports."""
    if not symbols:
        return ""
    try:
        from data.fetcher import fetch_stock_history
        from data.processor import get_latest_stats

        rows = ""
        for sym in symbols:
            df = fetch_stock_history(sym)
            if df is None or df.empty:
                continue
            stats = get_latest_stats(df)
            price = stats.get("price", 0)
            chg = stats.get("day_change_pct", 0)
            color = "#4ade80" if chg >= 0 else "#f87171"
            sign = "+" if chg >= 0 else ""
            rows += (
                f"<tr style='border-bottom:1px solid #1e293b'>"
                f"<td style='padding:8px;color:#fff;font-weight:600'>{sym.replace('.NS','').replace('.BO','')}</td>"
                f"<td style='padding:8px;color:#e2e8f0'>₹{price:,.2f}</td>"
                f"<td style='padding:8px;color:{color};font-weight:600'>{sign}{chg:.2f}%</td>"
                f"</tr>"
            )

        if not rows:
            return ""

        return f"""
        <div style="margin-top:24px">
          <p style="color:#94a3b8;font-size:13px;font-weight:600;margin:0 0 10px">⭐ Your Watchlist</p>
          <table style="width:100%;border-collapse:collapse;background:#12141e;border-radius:8px">
            <thead><tr style="border-bottom:1px solid #334155">
              <th style="padding:8px;color:#64748b;text-align:left;font-size:12px">Symbol</th>
              <th style="padding:8px;color:#64748b;text-align:left;font-size:12px">Price</th>
              <th style="padding:8px;color:#64748b;text-align:left;font-size:12px">Day %</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>"""
    except Exception:
        return ""


def _portfolio_section(holdings: list[dict]) -> str:
    """Build portfolio P&L HTML section for email reports."""
    if not holdings:
        return ""
    try:
        from data.fetcher import fetch_stock_history
        from data.processor import get_latest_stats

        total_invested = 0.0
        total_value = 0.0
        rows = ""

        for h in holdings:
            sym = h.get("symbol", "")
            qty = float(h.get("quantity", 0))
            avg_price = float(h.get("avg_buy_price", 0))
            invested = qty * avg_price

            df = fetch_stock_history(sym)
            current_price = avg_price  # fallback
            if df is not None and not df.empty:
                stats = get_latest_stats(df)
                current_price = stats.get("price", avg_price) or avg_price

            value = qty * current_price
            pnl = value - invested
            pnl_pct = (pnl / invested * 100) if invested > 0 else 0
            total_invested += invested
            total_value += value

            pnl_color = "#4ade80" if pnl >= 0 else "#f87171"
            sign = "+" if pnl >= 0 else ""
            rows += (
                f"<tr style='border-bottom:1px solid #1e293b'>"
                f"<td style='padding:8px;color:#fff;font-weight:600'>{sym.replace('.NS','').replace('.BO','')}</td>"
                f"<td style='padding:8px;color:#e2e8f0'>{qty:g}</td>"
                f"<td style='padding:8px;color:#e2e8f0'>₹{current_price:,.2f}</td>"
                f"<td style='padding:8px;color:{pnl_color};font-weight:600'>{sign}₹{pnl:,.0f} ({sign}{pnl_pct:.1f}%)</td>"
                f"</tr>"
            )

        if not rows:
            return ""

        total_pnl = total_value - total_invested
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        pnl_color = "#4ade80" if total_pnl >= 0 else "#f87171"
        sign = "+" if total_pnl >= 0 else ""

        summary_cards = (
            _card("Invested", f"₹{total_invested:,.0f}", "", "#e2e8f0") +
            _card("Current Value", f"₹{total_value:,.0f}", "", "#ffffff") +
            _card("Total P&L", f"{sign}₹{total_pnl:,.0f}", f"{sign}{total_pnl_pct:.1f}%", pnl_color)
        )

        return f"""
        <div style="margin-top:24px">
          <p style="color:#94a3b8;font-size:13px;font-weight:600;margin:0 0 10px">💼 Your Portfolio</p>
          <div style="margin-bottom:12px">{summary_cards}</div>
          <table style="width:100%;border-collapse:collapse;background:#12141e;border-radius:8px">
            <thead><tr style="border-bottom:1px solid #334155">
              <th style="padding:8px;color:#64748b;text-align:left;font-size:12px">Stock</th>
              <th style="padding:8px;color:#64748b;text-align:left;font-size:12px">Qty</th>
              <th style="padding:8px;color:#64748b;text-align:left;font-size:12px">Price</th>
              <th style="padding:8px;color:#64748b;text-align:left;font-size:12px">P&L</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>"""
    except Exception:
        return ""


def send_opening_report(to: str, watchlist_symbols: list[str] = None, portfolio_holdings: list[dict] = None):
    from data.fetcher import fetch_index_data, fetch_movers
    from config.settings import INDICES

    now = datetime.now(IST)
    date_str = now.strftime("%A, %d %B %Y")

    index_cards = ""
    for name, symbol in INDICES.items():
        d = fetch_index_data(symbol)
        if d:
            chg = d.get("change_pct", 0)
            color = "#4ade80" if chg >= 0 else "#f87171"
            sign = "+" if chg >= 0 else ""
            index_cards += _card(name, f"₹{d['current']:,.2f}", f"{sign}{chg:.2f}%", color)

    movers = fetch_movers()
    gainers_rows = "".join(
        f"<tr><td style='padding:6px 8px;color:#fff'>{g['symbol'].replace('.NS','')}</td>"
        f"<td style='padding:6px 8px;color:#4ade80;text-align:right'>+{g['change_pct']:.2f}%</td></tr>"
        for g in movers.get("gainers", [])
    )
    losers_rows = "".join(
        f"<tr><td style='padding:6px 8px;color:#fff'>{l['symbol'].replace('.NS','')}</td>"
        f"<td style='padding:6px 8px;color:#f87171;text-align:right'>{l['change_pct']:.2f}%</td></tr>"
        for l in movers.get("losers", [])
    )

    movers_html = f"""
    <div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:16px">
      <div style="flex:1;min-width:200px">
        <p style="color:#4ade80;font-size:13px;font-weight:600;margin:0 0 8px">▲ Top Gainers</p>
        <table style="width:100%;border-collapse:collapse">{gainers_rows}</table>
      </div>
      <div style="flex:1;min-width:200px">
        <p style="color:#f87171;font-size:13px;font-weight:600;margin:0 0 8px">▼ Top Losers</p>
        <table style="width:100%;border-collapse:collapse">{losers_rows}</table>
      </div>
    </div>"""

    watchlist_html = _watchlist_section(watchlist_symbols or [])
    portfolio_html = _portfolio_section(portfolio_holdings or [])

    body = f"""
    <div style="margin-bottom:20px">{index_cards}</div>
    {movers_html}
    {portfolio_html}
    {watchlist_html}
    <p style="color:#64748b;font-size:12px;margin-top:20px">Market opens at 9:15 AM IST. Good luck today! 🎯</p>"""

    html = _base_template("🌅 Market Opening Report", date_str, body)
    return _send(to, f"📈 Market Opening — {date_str}", html)


def send_closing_report(to: str, watchlist_symbols: list[str] = None, portfolio_holdings: list[dict] = None):
    from data.fetcher import fetch_index_data, fetch_movers
    from config.settings import INDICES

    now = datetime.now(IST)
    date_str = now.strftime("%A, %d %B %Y")

    index_cards = ""
    for name, symbol in INDICES.items():
        d = fetch_index_data(symbol)
        if d:
            chg = d.get("change_pct", 0)
            color = "#4ade80" if chg >= 0 else "#f87171"
            sign = "+" if chg >= 0 else ""
            index_cards += _card(name, f"₹{d['current']:,.2f}", f"{sign}{chg:.2f}%", color)

    movers = fetch_movers()
    gainers_rows = "".join(
        f"<tr><td style='padding:6px 8px;color:#fff'>{g['symbol'].replace('.NS','')}</td>"
        f"<td style='padding:6px 8px;color:#4ade80;text-align:right'>+{g['change_pct']:.2f}%</td></tr>"
        for g in movers.get("gainers", [])
    )
    losers_rows = "".join(
        f"<tr><td style='padding:6px 8px;color:#fff'>{l['symbol'].replace('.NS','')}</td>"
        f"<td style='padding:6px 8px;color:#f87171;text-align:right'>{l['change_pct']:.2f}%</td></tr>"
        for l in movers.get("losers", [])
    )

    movers_html = f"""
    <div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:16px">
      <div style="flex:1;min-width:200px">
        <p style="color:#4ade80;font-size:13px;font-weight:600;margin:0 0 8px">▲ Today's Gainers</p>
        <table style="width:100%;border-collapse:collapse">{gainers_rows}</table>
      </div>
      <div style="flex:1;min-width:200px">
        <p style="color:#f87171;font-size:13px;font-weight:600;margin:0 0 8px">▼ Today's Losers</p>
        <table style="width:100%;border-collapse:collapse">{losers_rows}</table>
      </div>
    </div>"""

    watchlist_html = _watchlist_section(watchlist_symbols or [])
    portfolio_html = _portfolio_section(portfolio_holdings or [])

    body = f"""
    <div style="margin-bottom:20px">{index_cards}</div>
    {movers_html}
    {portfolio_html}
    {watchlist_html}
    <p style="color:#64748b;font-size:12px;margin-top:20px">Market closed at 3:30 PM IST. See you tomorrow! 🌙</p>"""

    html = _base_template("🌇 Market Closing Report", date_str, body)
    return _send(to, f"📊 Market Closing — {date_str}", html)


def send_market_anomaly_alert(to: str, index_name: str, stats: dict, commentary: str):
    """Send an alert when a market index makes a statistically unusual move."""
    z = stats["z_score"]
    today_return = stats["today_return_pct"]
    current_price = stats["current_price"]
    direction = "surged" if z > 0 else "crashed"
    color = "#4ade80" if z > 0 else "#f87171"
    icon = "🚀" if z > 0 else "🔻"
    sign = "+" if today_return >= 0 else ""

    commentary_html = ""
    if commentary:
        lines = commentary.strip().replace("\n\n", "\n").split("\n")
        commentary_html = "".join(
            f"<p style='color:#e2e8f0;font-size:14px;margin:6px 0'>{line}</p>"
            for line in lines if line.strip()
        )

    body = f"""
    <p style="color:#94a3b8;font-size:13px;margin:0 0 16px">
      {icon} <strong style="color:{color}">{index_name}</strong> has made an unusually large move today.
      This is <strong style="color:#fff">{abs(z):.1f}x</strong> larger than its normal daily swing.
    </p>
    <div style="margin-bottom:20px">
      {_card("Current Level", f"₹{current_price:,.2f}", "", "#ffffff")}
      {_card("Today's Move", f"{sign}{today_return:.2f}%", f"Z-score: {z:+.2f}", color)}
      {_card("Normal Daily Move", f"±{abs(stats['std_pct']):.2f}%", "20-day avg volatility", "#94a3b8")}
    </div>
    <div style="background:#12141e;border-left:3px solid {color};border-radius:4px;padding:14px;margin-top:8px">
      <p style="color:#64748b;font-size:11px;font-weight:600;margin:0 0 8px;text-transform:uppercase">AI Analysis</p>
      {commentary_html or '<p style="color:#94a3b8;font-size:13px">No commentary available.</p>'}
    </div>"""

    now = datetime.now(IST)
    html = _base_template(
        f"{icon} Market Alert: {index_name} {direction.title()}",
        now.strftime("%A, %d %B %Y — %I:%M %p IST"),
        body,
    )
    subject = f"{icon} {index_name} {direction} {sign}{today_return:.2f}% — Unusual Market Move"
    return _send(to, subject, html)


def send_watchlist_spike_alert(to: str, symbol: str, stats: dict, commentary: str):
    """Send an alert when a watchlist stock makes a statistically unusual move."""
    sym_clean = symbol.replace(".NS", "").replace(".BO", "")
    z = stats["z_score"]
    today_return = stats["today_return_pct"]
    current_price = stats["current_price"]
    direction = "surged" if z > 0 else "dropped sharply"
    color = "#4ade80" if z > 0 else "#f87171"
    icon = "📈" if z > 0 else "📉"
    sign = "+" if today_return >= 0 else ""

    commentary_html = ""
    if commentary:
        lines = commentary.strip().replace("\n\n", "\n").split("\n")
        commentary_html = "".join(
            f"<p style='color:#e2e8f0;font-size:14px;margin:6px 0'>{line}</p>"
            for line in lines if line.strip()
        )

    body = f"""
    <p style="color:#94a3b8;font-size:13px;margin:0 0 16px">
      {icon} <strong style="color:#fff">{sym_clean}</strong> (from your watchlist) has {direction} today —
      <strong style="color:{color}">{sign}{today_return:.2f}%</strong>, which is
      <strong style="color:#fff">{abs(z):.1f}x</strong> larger than its normal daily move.
    </p>
    <div style="margin-bottom:20px">
      {_card("Current Price", f"₹{current_price:,.2f}", "", "#ffffff")}
      {_card("Today's Move", f"{sign}{today_return:.2f}%", f"Z-score: {z:+.2f}", color)}
      {_card("Normal Daily Move", f"±{abs(stats['std_pct']):.2f}%", "20-day avg volatility", "#94a3b8")}
    </div>
    <div style="background:#12141e;border-left:3px solid {color};border-radius:4px;padding:14px;margin-top:8px">
      <p style="color:#64748b;font-size:11px;font-weight:600;margin:0 0 8px;text-transform:uppercase">AI Analysis</p>
      {commentary_html or '<p style="color:#94a3b8;font-size:13px">No commentary available.</p>'}
    </div>"""

    now = datetime.now(IST)
    html = _base_template(
        f"{icon} Watchlist Alert: {sym_clean}",
        now.strftime("%A, %d %B %Y — %I:%M %p IST"),
        body,
    )
    subject = f"{icon} {sym_clean} {direction} {sign}{today_return:.2f}% — Unusual Move Detected"
    return _send(to, subject, html)


def send_price_alert(to: str, symbol: str, current_price: float, threshold: float, direction: str):
    sym_clean = symbol.replace(".NS", "").replace(".BO", "")
    direction_word = "risen above" if direction == "above" else "fallen below"
    color = "#4ade80" if direction == "above" else "#f87171"

    body = f"""
    <p style="color:#e2e8f0;font-size:15px">Your price alert for <strong style="color:#fff">{sym_clean}</strong> has been triggered.</p>
    <div style="margin:20px 0">
      {_card("Current Price", f"₹{current_price:,.2f}", f"Has {direction_word} ₹{threshold:,.2f}", color)}
    </div>
    <p style="color:#64748b;font-size:13px">Consider reviewing your position on the Stock Insights app.</p>"""

    html = _base_template(
        f"🔔 Price Alert: {sym_clean}",
        datetime.now(IST).strftime("%A, %d %B %Y — %I:%M %p IST"),
        body,
    )
    return _send(to, f"🔔 {sym_clean} has {direction_word} ₹{threshold:,.2f}", html)
