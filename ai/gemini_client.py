import os
from datetime import datetime
from ai.prompts import STOCK_INSIGHT_PROMPT, MARKET_OVERVIEW_PROMPT, TRENDING_COMMENTARY_PROMPT

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite"]


def _get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def _is_rate_limit(e: Exception) -> bool:
    return "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)


def _fmt_fund(value, unit):
    if value is None:
        return "N/A"
    return str(value) + unit


def _build_stock_prompt(symbol, company, stats, indicators, predictions, fundamentals=None):
    def _pred(label):
        r = predictions.get(label, {})
        price = r.get("predicted_price")
        pct = r.get("percent_change")
        cr = r.get("confidence_range", "N/A")
        return (
            str(price) if price else "N/A",
            f"{pct:+.2f}" if pct is not None else "N/A",
            cr,
        )

    p1w, pct1w, r1w = _pred("1 Week")
    p1m, pct1m, r1m = _pred("1 Month")
    p3m, pct3m, r3m = _pred("3 Months")
    p6m, pct6m, r6m = _pred("6 Months")

    fund = fundamentals or {}
    roce_val = _fmt_fund(fund.get("roce"), "%")
    roe_val = _fmt_fund(fund.get("roe"), "%")
    peg_val = _fmt_fund(fund.get("peg"), "x")

    return STOCK_INSIGHT_PROMPT.format(
        symbol=symbol, company=company,
        price=stats.get("price", "N/A"),
        day_change_pct=stats.get("day_change_pct", 0),
        week_52_high=stats.get("week_52_high", "N/A"),
        week_52_low=stats.get("week_52_low", "N/A"),
        volume_vs_avg=stats.get("volume_spike_pct", 0),
        rsi=indicators.get("rsi", "N/A"),
        rsi_signal=indicators.get("rsi_signal", "N/A"),
        macd_signal=indicators.get("macd_signal", "N/A"),
        bb_position=indicators.get("bb_position", "N/A"),
        ema_20=indicators.get("ema_20", "N/A"),
        ema_50=indicators.get("ema_50", "N/A"),
        trend=indicators.get("trend", "N/A"),
        roce=roce_val, roe=roe_val, peg=peg_val,
        pred_1w=p1w, pct_1w=pct1w, range_1w=r1w,
        pred_1m=p1m, pct_1m=pct1m, range_1m=r1m,
        pred_3m=p3m, pct_3m=pct3m, range_3m=r3m,
        pred_6m=p6m, pct_6m=pct6m, range_6m=r6m,
    )


def stream_stock_insight(symbol, company, stats, indicators, predictions, fundamentals=None):
    """Stream Gemini response token by token (generator)."""
    if not GEMINI_AVAILABLE:
        yield "⚠️ google-genai package not installed. Run: pip install google-genai"
        return

    client = _get_client()
    if client is None:
        yield "⚠️ Gemini API key not found. Add GEMINI_API_KEY to your .env file."
        return

    prompt = _build_stock_prompt(symbol, company, stats, indicators, predictions, fundamentals)
    for model in MODELS:
        try:
            for chunk in client.models.generate_content_stream(model=model, contents=prompt):
                if chunk.text:
                    yield chunk.text
            return
        except Exception as e:
            if _is_rate_limit(e) and model != MODELS[-1]:
                continue
            if _is_rate_limit(e):
                # Fall back to Groq
                from ai.groq_client import stream_groq
                yield from stream_groq(prompt)
            else:
                yield "⚠️ Error generating analysis. Please try again."
            return


def generate_market_overview(index_data: dict, movers: dict) -> str:
    """Generate a brief daily market narrative."""
    if not GEMINI_AVAILABLE:
        return ""
    client = _get_client()
    if client is None:
        return ""

    nifty = index_data.get("NIFTY 50", {})
    sensex = index_data.get("SENSEX", {})
    gainers_str = ", ".join(
        f"{g['symbol'].replace('.NS','').replace('.BO','')} ({g['change_pct']:+.2f}%)"
        for g in movers.get("gainers", [])
    )
    losers_str = ", ".join(
        f"{l['symbol'].replace('.NS','').replace('.BO','')} ({l['change_pct']:+.2f}%)"
        for l in movers.get("losers", [])
    )

    prompt = MARKET_OVERVIEW_PROMPT.format(
        date=datetime.now().strftime("%d %B %Y"),
        nifty=nifty.get("current", "N/A"),
        nifty_change=nifty.get("change_pct", 0),
        sensex=sensex.get("current", "N/A"),
        sensex_change=sensex.get("change_pct", 0),
        gainers=gainers_str or "N/A",
        losers=losers_str or "N/A",
    )
    for model in MODELS:
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            return response.text
        except Exception as e:
            if _is_rate_limit(e) and model != MODELS[-1]:
                continue
            if _is_rate_limit(e):
                from ai.groq_client import complete_groq
                return complete_groq(prompt)
            return ""
    return ""


def generate_trending_commentary(trending_df) -> str:
    """Generate brief commentary on trending stocks."""
    if not GEMINI_AVAILABLE or trending_df.empty:
        return ""
    client = _get_client()
    if client is None:
        return ""

    lines = [
        f"{row['name']}: Score {row['trending_score']}, "
        f"Day change {row['day_change_pct']:+.2f}%, "
        f"Volume spike {row['volume_spike_pct']:+.1f}%"
        for _, row in trending_df.head(5).iterrows()
    ]
    prompt = TRENDING_COMMENTARY_PROMPT.format(trending_data="\n".join(lines))
    for model in MODELS:
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            return response.text
        except Exception as e:
            if _is_rate_limit(e) and model != MODELS[-1]:
                continue
            if _is_rate_limit(e):
                from ai.groq_client import complete_groq
                return complete_groq(prompt)
            return ""
    return ""
