"""Precompute the canonical indicator set used by all seven systems.

Computing a single comprehensive feature set per symbol (rather than wiring
per-system indicator requirements through the engine) keeps the hot loop
branch-free and makes systems trivial to read: they just index NumPy arrays.

Expected input: a tidy OHLCV :class:`pandas.DataFrame` indexed by date with
columns ``open, high, low, close, volume`` (sorted ascending).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .. import indicators as ind
from ..core.system import Bars

OHLCV = ("open", "high", "low", "close", "volume")


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return ``df`` augmented with every indicator column the systems need."""
    df = df.copy()
    missing = [c for c in OHLCV if c not in df.columns]
    if missing:
        raise ValueError(f"OHLCV frame missing columns: {missing}")
    df = df.sort_index()

    h, l, c, v = df["high"], df["low"], df["close"], df["volume"]

    # Trend / moving averages
    for n in (25, 50, 100, 150, 200):
        df[f"sma_{n}"] = ind.sma(c, n)

    # Volatility
    df["atr_10"] = ind.atr(h, l, c, 10)
    df["atr_20"] = ind.atr(h, l, c, 20)
    df["atr_40"] = ind.atr(h, l, c, 40)
    df["atrp_10"] = ind.atr_percent(h, l, c, 10)
    df["hv_100"] = ind.historic_volatility(c, 100)

    # Momentum / oscillators
    df["rsi_3"] = ind.rsi(c, 3)
    df["rsi_4"] = ind.rsi(c, 4)
    df["adx_7"] = ind.adx(h, l, c, 7)
    df["roc_200"] = ind.roc(c, 200)

    # Liquidity
    df["advol_20"] = ind.avg_dollar_volume(c, v, 20)
    df["advol_50"] = ind.avg_dollar_volume(c, v, 50)
    df["avgvol_50"] = ind.avg_volume(v, 50)

    # Short-horizon returns (fractional)
    df["ret_3"] = ind.rolling_return(c, 3)
    df["ret_6"] = ind.rolling_return(c, 6)

    # Rolling extremes for the catastrophe hedge (System 7)
    df["lowest_close_50"] = c.rolling(50, min_periods=50).min()
    df["highest_close_70"] = c.rolling(70, min_periods=70).max()

    return df


def to_bars(symbol: str, df: pd.DataFrame) -> Bars:
    """Convert a feature-augmented frame into a column-oriented :class:`Bars`."""
    dates = df.index.to_pydatetime()
    dates = np.array([d.date() for d in dates], dtype=object)
    cols: dict[str, np.ndarray] = {}
    for name in df.columns:
        cols[name] = df[name].to_numpy(dtype="float64")
    return Bars(symbol, dates, cols)
