"""Optional real-data loader backed by yfinance.

Kept dependency-light: ``yfinance`` is only imported when this loader is used,
so the core engine and the synthetic pipeline have no third-party data deps.
Downloaded frames are cached as Parquet under ``cache_dir``.
"""

from __future__ import annotations

import os

import pandas as pd


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(
        columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Adj Close": "adj_close", "Volume": "volume",
        }
    )
    cols = ["open", "high", "low", "close", "volume"]
    df = df[[c for c in cols if c in df.columns]].copy()
    df.index = pd.to_datetime(df.index)
    return df.dropna()


def load_symbol(
    symbol: str,
    start: str,
    end: str,
    cache_dir: str = "data/cache",
) -> pd.DataFrame:
    """Download (or load from cache) a single symbol's OHLCV history."""
    os.makedirs(cache_dir, exist_ok=True)
    cache = os.path.join(cache_dir, f"{symbol}_{start}_{end}.parquet")
    if os.path.exists(cache):
        return pd.read_parquet(cache)

    import yfinance as yf  # local import: optional dependency

    raw = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        raise ValueError(f"no data returned for {symbol!r}")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    df = _normalise(raw)
    df.to_parquet(cache)
    return df


def load_universe(
    symbols: list[str],
    start: str,
    end: str,
    cache_dir: str = "data/cache",
) -> dict[str, pd.DataFrame]:
    universe: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        try:
            universe[sym] = load_symbol(sym, start, end, cache_dir)
        except Exception as exc:  # pragma: no cover - network dependent
            print(f"  ! skipped {sym}: {exc}")
    return universe
