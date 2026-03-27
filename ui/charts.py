import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from models.indicators import (
    compute_rsi, compute_macd, compute_bollinger_bands, compute_ema,
)


def plot_candlestick_with_indicators(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Three-panel chart: candlestick + Bollinger/EMA | Volume | RSI."""
    close = df["Close"]
    rsi = compute_rsi(close)
    macd_line, signal_line, histogram = compute_macd(close)
    bb_upper, bb_mid, bb_lower = compute_bollinger_bands(close)
    ema20 = compute_ema(close, 20)
    ema50 = compute_ema(close, 50)

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.60, 0.20, 0.20],
        vertical_spacing=0.03,
        subplot_titles=[f"{symbol} — Price", "Volume", "RSI (14)"],
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="Price", increasing_line_color="#00c853", decreasing_line_color="#ff1744",
        showlegend=False,
    ), row=1, col=1)

    # Bollinger Bands
    fig.add_trace(go.Scatter(x=df.index, y=bb_upper, name="BB Upper",
        line=dict(color="rgba(100,181,246,0.5)", width=1), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=bb_lower, name="BB Lower",
        line=dict(color="rgba(100,181,246,0.5)", width=1),
        fill="tonexty", fillcolor="rgba(100,181,246,0.05)", showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=bb_mid, name="BB Mid",
        line=dict(color="rgba(100,181,246,0.4)", width=1, dash="dot"), showlegend=False), row=1, col=1)

    # EMAs
    fig.add_trace(go.Scatter(x=df.index, y=ema20, name="EMA 20",
        line=dict(color="#ffd600", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ema50, name="EMA 50",
        line=dict(color="#ff6d00", width=1.5)), row=1, col=1)

    # Volume
    colors = ["#00c853" if c >= o else "#ff1744"
              for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
        marker_color=colors, showlegend=False), row=2, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=rsi, name="RSI",
        line=dict(color="#ab47bc", width=1.5), showlegend=False), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(255,23,68,0.5)", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(0,200,83,0.5)", row=3, col=1)
    fig.add_hrect(y0=30, y1=70, fillcolor="rgba(171,71,188,0.05)", line_width=0, row=3, col=1)

    fig.update_layout(
        template="plotly_dark",
        height=600,
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)")
    return fig


def plot_prediction_chart(
    historical_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    symbol: str,
    horizon_label: str,
) -> go.Figure:
    """Historical price + Prophet forecast with confidence band."""
    fig = go.Figure()

    # Historical
    fig.add_trace(go.Scatter(
        x=historical_df["ds"], y=historical_df["y"],
        name="Historical Price",
        line=dict(color="#64b5f6", width=2),
    ))

    # Confidence band
    fig.add_trace(go.Scatter(
        x=list(forecast_df["ds"]) + list(forecast_df["ds"])[::-1],
        y=list(forecast_df["yhat_upper"]) + list(forecast_df["yhat_lower"])[::-1],
        fill="toself",
        fillcolor="rgba(255,214,0,0.08)",
        line=dict(color="rgba(255,214,0,0)"),
        name="Confidence Band",
        showlegend=True,
    ))

    # Forecast line
    future_forecast = forecast_df[forecast_df["ds"] > historical_df["ds"].max()]
    fig.add_trace(go.Scatter(
        x=future_forecast["ds"], y=future_forecast["yhat"],
        name=f"Predicted ({horizon_label})",
        line=dict(color="#ffd600", width=2, dash="dash"),
    ))

    # Today vertical line
    today = historical_df["ds"].max()
    fig.add_vline(x=today, line_dash="dot", line_color="rgba(255,255,255,0.4)",
                  annotation_text="Today", annotation_position="top")

    fig.update_layout(
        template="plotly_dark",
        height=420,
        margin=dict(l=0, r=0, t=30, b=0),
        title=f"{symbol} — {horizon_label} Prediction",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)")
    return fig


def plot_movers_table(movers: list[dict], title: str) -> go.Figure:
    """A simple color-coded table for gainers/losers."""
    if not movers:
        return go.Figure()

    symbols = [m["symbol"].replace(".NS", "").replace(".BO", "") for m in movers]
    prices = [f"₹{m['price']:,.2f}" for m in movers]
    changes = [f"{'+' if m['change_pct'] >= 0 else ''}{m['change_pct']:.2f}%" for m in movers]
    is_gainer = title.lower().startswith("gain")
    cell_colors = [["#00c853" if is_gainer else "#ff1744"] * len(movers)] * 3

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=["<b>Stock</b>", "<b>Price</b>", "<b>Change</b>"],
            fill_color="#1e2130", font=dict(color="white", size=14),
            align="left", height=30,
        ),
        cells=dict(
            values=[symbols, prices, changes],
            fill_color=["#12141e", "#12141e", cell_colors[2]],
            font=dict(color=["white", "white", "white"], size=14),
            align="left", height=28,
        ),
    )])
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=0, r=0, t=0, b=0),
        height=200,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def plot_trending_treemap(trending_df: pd.DataFrame) -> go.Figure:
    """Treemap of trending stocks colored by day change %."""
    if trending_df.empty:
        return go.Figure()

    fig = go.Figure(go.Treemap(
        labels=trending_df["name"],
        parents=[""] * len(trending_df),
        values=trending_df["volume"],
        customdata=trending_df[["price", "day_change_pct", "trending_score"]],
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Price: ₹%{customdata[0]:,.2f}<br>"
            "Day Change: %{customdata[1]:+.2f}%<br>"
            "Trending Score: %{customdata[2]}<extra></extra>"
        ),
        marker=dict(
            colors=trending_df["day_change_pct"],
            colorscale=[[0, "#b71c1c"], [0.5, "#37474f"], [1, "#1b5e20"]],
            cmid=0,
            showscale=True,
            colorbar=dict(title="Day %"),
        ),
        textinfo="label+text",
        text=[f"{'+' if r >= 0 else ''}{r:.1f}%" for r in trending_df["day_change_pct"]],
    ))

    fig.update_layout(
        template="plotly_dark",
        height=420,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def plot_sparkline(series: pd.Series) -> go.Figure:
    """Minimal sparkline for index cards."""
    color = "#00c853" if float(series.iloc[-1]) >= float(series.iloc[0]) else "#ff1744"
    fig = go.Figure(go.Scatter(
        x=list(range(len(series))), y=series,
        mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor=color.replace(")", ",0.1)").replace("rgb", "rgba"),
    ))
    fig.update_layout(
        height=60, margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig
