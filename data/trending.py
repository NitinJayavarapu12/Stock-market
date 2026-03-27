import pandas as pd
import numpy as np
from data.fetcher import fetch_stock_history
from data.processor import compute_returns, compute_volume_metrics
from models.indicators import compute_rsi
from config.settings import NIFTY_50_SYMBOLS


def compute_trending_score(df: pd.DataFrame) -> float:
    """Composite 0-100 trending score based on volume spike, momentum, and RSI."""
    df = compute_returns(compute_volume_metrics(df))
    latest = df.iloc[-1]

    # Volume spike score (0-30)
    vol_spike = float(latest.get("volume_spike_pct", 0))
    vol_score = min(30, max(0, vol_spike / 5))  # 150% spike = 30 pts

    # Price momentum score (0-40)
    ret_1d = float(latest.get("ret_1d", 0))
    ret_5d = float(latest.get("ret_5d", 0))
    ret_20d = float(latest.get("ret_20d", 0))
    mom = ret_1d * 0.4 + ret_5d * 0.35 + ret_20d * 0.25
    mom_score = min(40, max(0, mom * 4))

    # RSI signal score (0-30)
    rsi_series = compute_rsi(df["Close"])
    rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50
    if 50 <= rsi <= 70:
        rsi_score = 30 * (rsi - 50) / 20
    elif rsi > 70:
        rsi_score = 15
    else:
        rsi_score = max(0, (rsi - 30) / 20 * 10)

    return round(vol_score + mom_score + rsi_score, 1)


def get_trending_stocks(symbols: list[str] = None, top_n: int = 10) -> pd.DataFrame:
    """Return top_n trending stocks sorted by composite score."""
    symbols = symbols or NIFTY_50_SYMBOLS
    rows = []

    for sym in symbols:
        df = fetch_stock_history(sym, days=60)
        if df is None or len(df) < 25:
            continue
        try:
            score = compute_trending_score(df)
            latest = df.iloc[-1]
            prev_close = float(df.iloc[-2]["Close"]) if len(df) > 1 else float(latest["Close"])
            price = float(latest["Close"])
            day_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0
            vol_spike = float(
                (latest["Volume"] - df["Volume"].tail(20).mean()) / df["Volume"].tail(20).mean() * 100
            )
            rows.append({
                "symbol": sym,
                "name": sym.replace(".NS", "").replace(".BO", ""),
                "price": round(price, 2),
                "day_change_pct": day_pct,
                "trending_score": score,
                "volume_spike_pct": round(vol_spike, 1),
                "volume": int(latest["Volume"]),
            })
        except Exception:
            continue

    df_out = pd.DataFrame(rows)
    if df_out.empty:
        return df_out
    return df_out.sort_values("trending_score", ascending=False).head(top_n).reset_index(drop=True)
