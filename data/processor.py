import pandas as pd
import numpy as np


def compute_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Add return columns: ret_1d, ret_5d, ret_20d, ret_60d."""
    close = df["Close"]
    df = df.copy()
    df["ret_1d"] = close.pct_change(1) * 100
    df["ret_5d"] = close.pct_change(5) * 100
    df["ret_20d"] = close.pct_change(20) * 100
    df["ret_60d"] = close.pct_change(60) * 100
    return df


def compute_volume_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add volume_avg_20d and volume_spike_pct columns."""
    df = df.copy()
    df["volume_avg_20d"] = df["Volume"].rolling(20).mean()
    df["volume_spike_pct"] = (
        (df["Volume"] - df["volume_avg_20d"]) / df["volume_avg_20d"] * 100
    )
    return df


def get_latest_stats(df: pd.DataFrame) -> dict:
    """Return a flat dict of latest price + computed stats for display."""
    df = compute_returns(compute_volume_metrics(df))
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    return {
        "price": round(float(latest["Close"]), 2),
        "open": round(float(latest["Open"]), 2),
        "high": round(float(latest["High"]), 2),
        "low": round(float(latest["Low"]), 2),
        "volume": int(latest["Volume"]),
        "prev_close": round(float(prev["Close"]), 2),
        "day_change": round(float(latest["Close"]) - float(prev["Close"]), 2),
        "day_change_pct": round(float(latest.get("ret_1d", 0)), 2),
        "ret_5d": round(float(latest.get("ret_5d", 0)), 2),
        "ret_20d": round(float(latest.get("ret_20d", 0)), 2),
        "ret_60d": round(float(latest.get("ret_60d", 0)), 2),
        "week_52_high": round(float(df["High"].tail(252).max()), 2),
        "week_52_low": round(float(df["Low"].tail(252).min()), 2),
        "volume_spike_pct": round(float(latest.get("volume_spike_pct", 0)), 1),
    }


def format_inr(value: float) -> str:
    """Format a number as Indian Rupees."""
    return f"₹{value:,.2f}"


def format_pct(value: float, sign: bool = True) -> str:
    prefix = "+" if sign and value > 0 else ""
    return f"{prefix}{value:.2f}%"
