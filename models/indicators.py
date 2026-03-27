import pandas as pd
import numpy as np


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def compute_macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (macd_line, signal_line, histogram)."""
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal
    return macd, signal, histogram


def compute_bollinger_bands(
    close: pd.Series, period: int = 20, std_dev: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (upper_band, middle_band, lower_band)."""
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return upper, mid, lower


def compute_ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False).mean()


def compute_support_resistance(df: pd.DataFrame, window: int = 20) -> dict:
    """Simple pivot-point based support/resistance from last `window` sessions."""
    recent = df.tail(window)
    pivot = (recent["High"].mean() + recent["Low"].mean() + recent["Close"].mean()) / 3
    resistance1 = 2 * pivot - recent["Low"].mean()
    support1 = 2 * pivot - recent["High"].mean()
    return {
        "pivot": round(float(pivot), 2),
        "resistance1": round(float(resistance1), 2),
        "support1": round(float(support1), 2),
        "week_high": round(float(recent["High"].max()), 2),
        "week_low": round(float(recent["Low"].min()), 2),
    }


def get_rsi_signal(rsi: float) -> str:
    if rsi >= 70:
        return "Overbought"
    elif rsi >= 55:
        return "Bullish"
    elif rsi >= 45:
        return "Neutral"
    elif rsi >= 30:
        return "Bearish"
    return "Oversold"


def get_macd_signal(macd: float, signal: float, histogram: float) -> str:
    if macd > signal and histogram > 0:
        return "Bullish Crossover"
    elif macd < signal and histogram < 0:
        return "Bearish Crossover"
    elif macd > 0:
        return "Bullish"
    return "Bearish"


def get_bb_position(close: float, upper: float, lower: float, mid: float) -> str:
    if close >= upper:
        return "Above Upper Band (Overbought)"
    elif close <= lower:
        return "Below Lower Band (Oversold)"
    elif close >= mid:
        return "Above Mid Band (Positive)"
    return "Below Mid Band (Caution)"


def get_indicator_summary(df: pd.DataFrame) -> dict:
    """Return a flat dict of all indicators + signals for the latest bar."""
    close = df["Close"]

    rsi_series = compute_rsi(close)
    macd_line, signal_line, histogram = compute_macd(close)
    bb_upper, bb_mid, bb_lower = compute_bollinger_bands(close)
    ema20 = compute_ema(close, 20)
    ema50 = compute_ema(close, 50)

    rsi = float(rsi_series.iloc[-1])
    macd_val = float(macd_line.iloc[-1])
    signal_val = float(signal_line.iloc[-1])
    hist_val = float(histogram.iloc[-1])
    close_val = float(close.iloc[-1])
    ema20_val = float(ema20.iloc[-1])
    ema50_val = float(ema50.iloc[-1])
    upper_val = float(bb_upper.iloc[-1])
    lower_val = float(bb_lower.iloc[-1])
    mid_val = float(bb_mid.iloc[-1])

    vol_avg = float(df["Volume"].tail(20).mean())
    vol_today = float(df["Volume"].iloc[-1])
    vol_vs_avg = round((vol_today - vol_avg) / vol_avg * 100, 1) if vol_avg else 0

    trend = "Bullish" if ema20_val > ema50_val else "Bearish"

    return {
        "rsi": round(rsi, 1),
        "rsi_signal": get_rsi_signal(rsi),
        "macd": round(macd_val, 3),
        "macd_signal_line": round(signal_val, 3),
        "macd_histogram": round(hist_val, 3),
        "macd_signal": get_macd_signal(macd_val, signal_val, hist_val),
        "bb_upper": round(upper_val, 2),
        "bb_mid": round(mid_val, 2),
        "bb_lower": round(lower_val, 2),
        "bb_position": get_bb_position(close_val, upper_val, lower_val, mid_val),
        "ema_20": round(ema20_val, 2),
        "ema_50": round(ema50_val, 2),
        "trend": trend,
        "volume_vs_avg_pct": vol_vs_avg,
    }
