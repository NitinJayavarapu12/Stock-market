import yfinance as yf
import pandas as pd
from datetime import datetime, time
import pytz
from typing import Optional
from data import cache as stock_cache
from config.settings import (
    NIFTY_50_SYMBOLS, INDICES, HISTORY_DAYS_DEFAULT, HISTORY_DAYS_PREDICTION,
    IST, NSE_OPEN_HOUR, NSE_OPEN_MIN, NSE_CLOSE_HOUR, NSE_CLOSE_MIN,
)


def _normalize_symbol(symbol: str) -> str:
    """Add .NS suffix if no exchange suffix provided."""
    if "." not in symbol:
        return symbol + ".NS"
    return symbol


def fetch_stock_history(symbol: str, days: int = HISTORY_DAYS_DEFAULT) -> Optional[pd.DataFrame]:
    """Fetch OHLCV history. Falls back from .NS to .BO if empty."""
    symbol = _normalize_symbol(symbol)

    # Check cache first (only for default history length)
    if days == HISTORY_DAYS_DEFAULT and not stock_cache.is_stale(symbol):
        cached = stock_cache.get(symbol)
        if cached is not None and not cached.empty:
            return cached

    df = _download(symbol, days)
    if df is None or df.empty:
        fallback = symbol.replace(".NS", ".BO")
        if fallback != symbol:
            df = _download(fallback, days)

    if df is None or df.empty:
        return None

    # Flatten MultiIndex columns if batch download created them
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()

    if days == HISTORY_DAYS_DEFAULT:
        stock_cache.set(symbol, df)

    return df


def _download(symbol: str, days: int) -> pd.DataFrame:
    try:
        df = yf.download(
            symbol,
            period=f"{days}d",
            progress=False,
            auto_adjust=True,
            actions=False,
        )
        return df
    except Exception:
        return pd.DataFrame()


def fetch_multiple_stocks(symbols: list[str]) -> dict[str, pd.DataFrame]:
    """Batch fetch last 5 days for a list of symbols (used on Dashboard)."""
    results = {}
    for sym in symbols:
        df = fetch_stock_history(sym, days=30)
        if df is not None and not df.empty:
            results[sym] = df
    return results


def fetch_index_data(index_symbol: str) -> dict:
    """Return current value, day change, and pct change for an index."""
    try:
        ticker = yf.Ticker(index_symbol)
        info = ticker.fast_info
        current = info.last_price
        prev_close = info.previous_close
        if current is None or prev_close is None:
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                current = float(hist["Close"].iloc[-1])
                prev_close = float(hist["Close"].iloc[-2])
            elif len(hist) == 1:
                current = float(hist["Close"].iloc[-1])
                prev_close = current
            else:
                return {}
        change = current - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else 0
        return {
            "current": round(current, 2),
            "prev_close": round(prev_close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
        }
    except Exception:
        return {}


def fetch_movers(symbols: list[str] = None) -> dict:
    """Return top 5 gainers and losers from NIFTY 50."""
    symbols = symbols or NIFTY_50_SYMBOLS
    rows = []
    data = {}
    try:
        raw = yf.download(
            symbols,
            period="5d",
            progress=False,
            auto_adjust=True,
            actions=False,
            group_by="ticker",
        )
        for sym in symbols:
            try:
                if isinstance(raw.columns, pd.MultiIndex):
                    closes = raw[sym]["Close"].dropna()
                else:
                    closes = raw["Close"].dropna()
                if len(closes) >= 2:
                    prev = float(closes.iloc[-2])
                    curr = float(closes.iloc[-1])
                    pct = round((curr - prev) / prev * 100, 2) if prev else 0
                    rows.append({"symbol": sym, "price": round(curr, 2), "change_pct": pct})
            except Exception:
                continue
    except Exception:
        pass

    rows_sorted = sorted(rows, key=lambda x: x["change_pct"], reverse=True)
    data["gainers"] = [r for r in rows_sorted if r["change_pct"] > 0][:5]
    data["losers"] = [r for r in reversed(rows_sorted) if r["change_pct"] < 0][:5]
    return data


def is_market_open() -> bool:
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    t = now.time()
    return time(NSE_OPEN_HOUR, NSE_OPEN_MIN) <= t <= time(NSE_CLOSE_HOUR, NSE_CLOSE_MIN)


def get_market_status_label() -> str:
    if is_market_open():
        return "🟢 Market Open (NSE)"
    return "🔴 Market Closed"


def fetch_fundamentals(symbol: str) -> dict:
    """Fetch ROE, ROCE, PEG for a symbol via yf.Ticker.info. Never raises."""
    symbol = _normalize_symbol(symbol)

    def _fetch_info(sym: str) -> Optional[dict]:
        try:
            info = yf.Ticker(sym).info
            if not info or info.get("regularMarketPrice") is None:
                return None
            return info
        except Exception:
            return None

    info = _fetch_info(symbol)
    if info is None:
        fallback = symbol.replace(".NS", ".BO")
        if fallback != symbol:
            info = _fetch_info(fallback)

    if info is None:
        return {"roe": None, "roce": None, "peg": None}

    raw_roe = info.get("returnOnEquity")
    roe = round(raw_roe * 100, 2) if raw_roe is not None else None

    raw_peg = info.get("pegRatio")
    peg = round(float(raw_peg), 2) if raw_peg is not None else None

    ebitda = info.get("ebitda")
    total_assets = info.get("totalAssets")
    current_liabilities = info.get("currentLiabilities")
    roce = None
    if ebitda and total_assets and current_liabilities:
        capital_employed = total_assets - current_liabilities
        if capital_employed > 0:
            roce = round((ebitda / capital_employed) * 100, 2)

    return {"roe": roe, "roce": roce, "peg": peg}


def search_stocks(query: str, top_n: int = 10) -> list[dict]:
    """Fuzzy search over bundled NSE symbol list."""
    from pathlib import Path
    import csv

    csv_path = Path(__file__).parent / "symbol_list.csv"
    if not csv_path.exists():
        # Fallback: search NIFTY 50 only
        results = []
        q = query.upper()
        for sym in NIFTY_50_SYMBOLS:
            name = sym.replace(".NS", "")
            if q in name:
                results.append({"symbol": sym, "company": name, "exchange": "NSE"})
        return results[:top_n]

    try:
        from fuzzywuzzy import process
        rows = []
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)

        choices = {r["symbol"] + " " + r.get("company", ""): r for r in rows}
        matches = process.extract(query, list(choices.keys()), limit=top_n)
        return [choices[m[0]] for m in matches if m[1] > 40]
    except Exception:
        return []
