"""Reproducible synthetic OHLCV generator.

Lets the whole pipeline (and the test-suite) run with zero network access while
still exercising every code path: trends, pullbacks, overbought spikes, regime
switches in the market index, and varied liquidity/volatility profiles.

A geometric random walk with a slowly drifting trend produces realistic-looking
bars; the market index ("SPY") gets explicit bull/bear regimes so that the
trend filters and the catastrophe hedge actually trigger.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

BUSINESS_DAYS = "B"


def _ohlc_from_close(close: np.ndarray, rng: np.random.Generator, vol: float) -> pd.DataFrame:
    n = len(close)
    intraday = np.abs(rng.normal(0, vol, n)) * close
    high = close + intraday * rng.uniform(0.2, 1.0, n)
    low = close - intraday * rng.uniform(0.2, 1.0, n)
    open_ = low + (high - low) * rng.uniform(0.0, 1.0, n)
    high = np.maximum.reduce([high, open_, close])
    low = np.minimum.reduce([low, open_, close])
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})


def make_market(dates: pd.DatetimeIndex, seed: int = 7) -> pd.DataFrame:
    """SPY-like series with alternating bull/bear regimes and a 2008-style crash."""
    rng = np.random.default_rng(seed)
    n = len(dates)
    drift = np.empty(n)
    # Regime blocks: mostly up, with two sharp drawdowns.
    block = max(n // 8, 1)
    regimes = [0.0006, 0.0008, -0.0015, 0.0009, 0.0007, -0.0025, 0.0010, 0.0008]
    for k in range(0, n, block):
        drift[k : k + block] = regimes[(k // block) % len(regimes)]
    shocks = rng.normal(0, 0.009, n)
    log_ret = drift + shocks
    close = 100.0 * np.exp(np.cumsum(log_ret))
    df = _ohlc_from_close(close, rng, vol=0.006)
    df["volume"] = rng.integers(80_000_000, 160_000_000, n)
    df.index = dates
    return df


def make_stock(
    dates: pd.DatetimeIndex,
    seed: int,
    base_price: float = 50.0,
    annual_drift: float = 0.10,
    annual_vol: float = 0.35,
    avg_volume: float = 3_000_000,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = len(dates)
    dt = 1.0 / 252.0
    mu = annual_drift * dt
    sigma = annual_vol * np.sqrt(dt)
    log_ret = rng.normal(mu, sigma, n)
    # Inject occasional gap-down selloffs and momentum bursts for MR/short setups.
    for t in range(5, n):
        u = rng.random()
        if u < 0.01:
            log_ret[t] -= rng.uniform(0.10, 0.18)   # sharp 3-day-style selloff
        elif u > 0.99:
            log_ret[t] += rng.uniform(0.08, 0.14)    # overbought spike
    close = base_price * np.exp(np.cumsum(log_ret))
    close = np.maximum(close, 1.0)
    df = _ohlc_from_close(close, rng, vol=annual_vol * np.sqrt(dt) * 0.8)
    vol_noise = rng.uniform(0.5, 1.8, n)
    df["volume"] = (avg_volume * vol_noise).astype("int64")
    df.index = dates
    return df


def make_universe(
    n_stocks: int = 40,
    start: str = "2005-01-01",
    end: str = "2019-12-31",
    seed: int = 0,
    market_symbol: str = "SPY",
) -> dict[str, pd.DataFrame]:
    """Return a ``{symbol: OHLCV DataFrame}`` universe including the market."""
    dates = pd.bdate_range(start=start, end=end)
    rng = np.random.default_rng(seed)
    universe: dict[str, pd.DataFrame] = {market_symbol: make_market(dates, seed=seed + 7)}
    for k in range(n_stocks):
        sym = f"STK{k:03d}"
        universe[sym] = make_stock(
            dates,
            seed=seed * 1000 + k,
            base_price=float(rng.uniform(8, 120)),
            annual_drift=float(rng.uniform(-0.05, 0.25)),
            annual_vol=float(rng.uniform(0.20, 0.60)),
            avg_volume=float(rng.uniform(1_000_000, 20_000_000)),
        )
    return universe
