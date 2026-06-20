"""Optional real-data loader backed by yfinance.

Kept dependency-light: ``yfinance`` is only imported when this loader is used,
so the core engine and the synthetic pipeline have no third-party data deps.
Downloaded frames are cached as CSV under ``cache_dir`` (no parquet engine
required); set ``ASTS_CACHE_PARQUET=1`` to prefer Parquet when pyarrow is
available.
"""

from __future__ import annotations

import os

import pandas as pd

_USE_PARQUET = os.environ.get("ASTS_CACHE_PARQUET") == "1"


def _read_cache(path_no_ext: str) -> pd.DataFrame | None:
    if _USE_PARQUET and os.path.exists(path_no_ext + ".parquet"):
        try:
            return pd.read_parquet(path_no_ext + ".parquet")
        except Exception:
            pass
    if os.path.exists(path_no_ext + ".csv"):
        return pd.read_csv(path_no_ext + ".csv", index_col=0, parse_dates=True)
    return None


def _write_cache(df: pd.DataFrame, path_no_ext: str) -> None:
    if _USE_PARQUET:
        try:
            df.to_parquet(path_no_ext + ".parquet")
            return
        except Exception:
            pass  # fall back to CSV if no parquet engine is installed
    df.to_csv(path_no_ext + ".csv")


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
    cache = os.path.join(cache_dir, f"{symbol}_{start}_{end}")
    cached = _read_cache(cache)
    if cached is not None:
        return cached

    import yfinance as yf  # local import: optional dependency

    raw = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        raise ValueError(f"no data returned for {symbol!r}")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    df = _normalise(raw)
    _write_cache(df, cache)
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
