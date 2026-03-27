import pandas as pd
import numpy as np
from config.settings import PREDICTION_HORIZONS, HISTORY_DAYS_PREDICTION

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False


def _prepare_prophet_df(df: pd.DataFrame) -> pd.DataFrame:
    """Convert OHLCV dataframe to Prophet's ds/y format."""
    prophet_df = df[["Close"]].copy()
    prophet_df.index = pd.to_datetime(prophet_df.index)
    prophet_df = prophet_df.reset_index()
    prophet_df.columns = ["ds", "y"]
    prophet_df["ds"] = prophet_df["ds"].dt.tz_localize(None)
    return prophet_df


def run_prophet_prediction(df: pd.DataFrame, horizon_days: int) -> dict:
    """Run Prophet for a single horizon. Returns prediction result dict."""
    if not PROPHET_AVAILABLE:
        return _fallback_prediction(df, horizon_days)

    prophet_df = _prepare_prophet_df(df)
    if len(prophet_df) < 60:
        return _fallback_prediction(df, horizon_days)

    try:
        import holidays as hols
        indian_holidays = hols.India()
        holiday_list = [
            {"holiday": name, "ds": pd.Timestamp(date), "lower_window": 0, "upper_window": 1}
            for date, name in list(indian_holidays.items())
            if pd.Timestamp(date) >= prophet_df["ds"].min()
        ]
        holidays_df = pd.DataFrame(holiday_list) if holiday_list else None
    except Exception:
        holidays_df = None

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,
        holidays=holidays_df,
        interval_width=0.80,
    )
    model.fit(prophet_df)

    future = model.make_future_dataframe(periods=horizon_days)
    forecast = model.predict(future)

    current_price = float(df["Close"].iloc[-1])
    forecast_tail = forecast.tail(horizon_days)
    predicted_price = float(forecast_tail["yhat"].iloc[-1])
    predicted_low = float(forecast_tail["yhat_lower"].iloc[-1])
    predicted_high = float(forecast_tail["yhat_upper"].iloc[-1])
    pct_change = round((predicted_price - current_price) / current_price * 100, 2)

    trend = "Upward" if pct_change > 1 else ("Downward" if pct_change < -1 else "Sideways")

    return {
        "forecast_df": forecast,
        "historical_df": prophet_df,
        "current_price": round(current_price, 2),
        "predicted_price": round(predicted_price, 2),
        "predicted_low": round(max(predicted_low, 0), 2),
        "predicted_high": round(predicted_high, 2),
        "percent_change": pct_change,
        "confidence_range": f"₹{max(predicted_low, 0):,.0f} – ₹{predicted_high:,.0f}",
        "trend_direction": trend,
        "error": None,
    }


def _fallback_prediction(df: pd.DataFrame, horizon_days: int) -> dict:
    """Simple linear regression fallback if Prophet is unavailable."""
    close = df["Close"].values
    x = np.arange(len(close))
    coeffs = np.polyfit(x, close, 1)
    slope = coeffs[0]
    current = float(close[-1])
    predicted = float(current + slope * horizon_days)
    std = float(np.std(close[-60:])) if len(close) >= 60 else float(np.std(close))
    low = max(predicted - 1.5 * std, 0)
    high = predicted + 1.5 * std
    pct = round((predicted - current) / current * 100, 2) if current else 0
    trend = "Upward" if pct > 1 else ("Downward" if pct < -1 else "Sideways")
    return {
        "forecast_df": None,
        "historical_df": None,
        "current_price": round(current, 2),
        "predicted_price": round(predicted, 2),
        "predicted_low": round(low, 2),
        "predicted_high": round(high, 2),
        "percent_change": pct,
        "confidence_range": f"₹{low:,.0f} – ₹{high:,.0f}",
        "trend_direction": trend,
        "error": "Using simplified model (Prophet not installed)",
    }


def predict_all_horizons(df: pd.DataFrame, symbol: str) -> dict[str, dict]:
    """Run predictions for all horizons defined in settings."""
    results = {}
    for label, days in PREDICTION_HORIZONS.items():
        try:
            results[label] = run_prophet_prediction(df, days)
        except Exception as e:
            results[label] = {
                "error": str(e),
                "current_price": float(df["Close"].iloc[-1]),
                "predicted_price": None,
                "trend_direction": "Unknown",
                "percent_change": None,
                "confidence_range": "N/A",
                "forecast_df": None,
                "historical_df": None,
            }
    return results
