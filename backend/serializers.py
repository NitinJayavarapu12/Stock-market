import math
import pandas as pd


def df_to_records(df: pd.DataFrame) -> list:
    """Convert OHLCV DataFrame (DatetimeIndex) to list of JSON-serializable dicts."""
    df_copy = df.reset_index()
    # Rename the first column (Date / Datetime) to 'date'
    df_copy = df_copy.rename(columns={df_copy.columns[0]: "date"})
    df_copy.columns = [c.lower() for c in df_copy.columns]
    df_copy["date"] = pd.to_datetime(df_copy["date"]).dt.strftime("%Y-%m-%d")
    records = df_copy.to_dict(orient="records")
    # Replace NaN with None for JSON compatibility
    return [
        {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items()}
        for r in records
    ]


def prediction_to_json(result: dict) -> dict:
    """Strip DataFrames from a Prophet result dict, convert to serializable arrays."""
    out = {k: v for k, v in result.items() if k not in ("forecast_df", "historical_df")}

    forecast_df = result.get("forecast_df")
    historical_df = result.get("historical_df")

    if forecast_df is not None and not forecast_df.empty:
        cols = ["ds", "yhat", "yhat_lower", "yhat_upper"]
        sub = forecast_df[cols].copy()
        sub["ds"] = pd.to_datetime(sub["ds"]).dt.strftime("%Y-%m-%d")
        out["forecast_points"] = sub.to_dict(orient="records")
    else:
        out["forecast_points"] = []

    if historical_df is not None and not historical_df.empty:
        hist = historical_df.copy()
        hist["ds"] = pd.to_datetime(hist["ds"]).dt.strftime("%Y-%m-%d")
        out["historical_points"] = hist.to_dict(orient="records")
    else:
        out["historical_points"] = []

    return out
