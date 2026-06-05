from typing import Optional
import pandas as pd


def screen_buy_opportunities(symbols: list) -> list:
    """
    Screen a list of symbols for technical buy signals.

    Scoring (max 80 pts before Prophet):
      - RSI 30-50 recovery zone:     +15 pts
      - MACD Bullish Crossover:      +15 pts
      - BB below lower band:         +10 pts
      - Trending score (0-100→0-40): 0-40 pts

    Only stocks with composite >= 50 are returned, sorted descending.
    Caller is responsible for running Prophet on the top candidates.
    """
    from data.fetcher import fetch_stock_history
    from data.processor import get_latest_stats
    from models.indicators import get_indicator_summary
    from data.trending import compute_trending_score

    candidates = []

    for symbol in symbols:
        try:
            df = fetch_stock_history(symbol)
            if df is None or len(df) < 60:
                continue

            indicators = get_indicator_summary(df)
            trending_score = compute_trending_score(df)
            stats = get_latest_stats(df)
        except Exception:
            continue

        rsi = indicators.get("rsi", 50)
        macd_signal = indicators.get("macd_signal", "")
        bb_position = str(indicators.get("bb_position", ""))

        tech_score = 0
        if isinstance(rsi, (int, float)) and 30 <= rsi <= 50:
            tech_score += 15
        if macd_signal == "Bullish Crossover":
            tech_score += 15
        if bb_position.startswith("Below Lower Band"):
            tech_score += 10

        trending_scaled = round(float(trending_score or 0) / 100 * 40, 1)
        composite = tech_score + trending_scaled

        if composite < 50:
            continue

        candidates.append({
            "symbol": symbol,
            "company": symbol.replace(".NS", "").replace(".BO", ""),
            "composite_score": round(composite, 1),
            "technical_score": tech_score,
            "trending_score": round(float(trending_score or 0), 1),
            "rsi": round(float(rsi), 1) if isinstance(rsi, (int, float)) else rsi,
            "macd_signal": macd_signal,
            "bb_position": bb_position,
            "price": stats.get("price", 0),
            "day_change_pct": stats.get("day_change_pct", 0),
            "stats": stats,
            "indicators": indicators,
            "df": df,
        })

    return sorted(candidates, key=lambda x: x["composite_score"], reverse=True)
