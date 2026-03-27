import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent / "stocks.db"
CACHE_TTL_MINUTES = 15


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            symbol TEXT,
            date TEXT,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            PRIMARY KEY (symbol, date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache_meta (
            symbol TEXT PRIMARY KEY,
            last_updated TEXT
        )
    """)
    conn.commit()
    return conn


def is_stale(symbol: str) -> bool:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT last_updated FROM cache_meta WHERE symbol = ?", (symbol,)
        ).fetchone()
    if row is None:
        return True
    last = datetime.fromisoformat(row[0])
    return datetime.utcnow() - last > timedelta(minutes=CACHE_TTL_MINUTES)


def get(symbol: str) -> Optional[pd.DataFrame]:
    with _get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT date, open, high, low, close, volume FROM price_history WHERE symbol = ? ORDER BY date",
            conn,
            params=(symbol,),
        )
    if df.empty:
        return None
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    df.columns = [c.capitalize() for c in df.columns]
    return df


def set(symbol: str, df: pd.DataFrame) -> None:
    rows = []
    for date, row in df.iterrows():
        rows.append((
            symbol,
            str(date.date()) if hasattr(date, "date") else str(date),
            float(row.get("Open", row.get("open", 0))),
            float(row.get("High", row.get("high", 0))),
            float(row.get("Low", row.get("low", 0))),
            float(row.get("Close", row.get("close", 0))),
            float(row.get("Volume", row.get("volume", 0))),
        ))
    with _get_conn() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO price_history VALUES (?,?,?,?,?,?,?)", rows
        )
        conn.execute(
            "INSERT OR REPLACE INTO cache_meta VALUES (?, ?)",
            (symbol, datetime.utcnow().isoformat()),
        )
        conn.commit()
