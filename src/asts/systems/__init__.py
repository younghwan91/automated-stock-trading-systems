"""The seven non-correlated trading systems and named suites.

Suites mirror the equity allocations Bensdorp uses in the book. Because long and
short books are run simultaneously (100% long + 100% short), the long systems'
allocations sum to 1.0 and the short systems' allocations sum to 1.0
independently.
"""

from __future__ import annotations

from ..core.types import SizingParams
from .system1_long_trend_high_momentum import System1LongTrendHighMomentum
from .system2_short_rsi_thrust import System2ShortRSIThrust
from .system3_long_mr_selloff import System3LongMeanReversionSelloff
from .system4_long_trend_low_volatility import System4LongTrendLowVolatility
from .system5_long_mr_adx_reversal import System5LongMeanReversionADXReversal
from .system6_short_mr_six_day_surge import System6ShortMeanReversionSixDaySurge
from .system7_catastrophe_hedge import System7CatastropheHedge

__all__ = [
    "System1LongTrendHighMomentum",
    "System2ShortRSIThrust",
    "System3LongMeanReversionSelloff",
    "System4LongTrendLowVolatility",
    "System5LongMeanReversionADXReversal",
    "System6ShortMeanReversionSixDaySurge",
    "System7CatastropheHedge",
    "SYSTEM_REGISTRY",
    "build_suite",
]

SYSTEM_REGISTRY = {
    "s1": System1LongTrendHighMomentum,
    "s2": System2ShortRSIThrust,
    "s3": System3LongMeanReversionSelloff,
    "s4": System4LongTrendLowVolatility,
    "s5": System5LongMeanReversionADXReversal,
    "s6": System6ShortMeanReversionSixDaySurge,
    "s7": System7CatastropheHedge,
}


def _sized(cls, allocation: float):
    return cls(SizingParams(allocation=allocation))


def build_suite(name: str):
    """Return a list of instantiated systems for a named suite."""
    name = name.lower()
    if name in SYSTEM_REGISTRY:  # a single system, full allocation
        return [SYSTEM_REGISTRY[name]()]

    if name == "suite3":  # Chapter 7: Systems 1, 2, 3
        return [
            _sized(System1LongTrendHighMomentum, 0.50),
            _sized(System3LongMeanReversionSelloff, 0.50),
            _sized(System2ShortRSIThrust, 1.00),
        ]
    if name == "suite6":  # Chapter 9: Systems 1, 3, 4, 5 long + 2, 6 short
        return [
            _sized(System1LongTrendHighMomentum, 0.25),
            _sized(System4LongTrendLowVolatility, 0.25),
            _sized(System3LongMeanReversionSelloff, 0.25),
            _sized(System5LongMeanReversionADXReversal, 0.25),
            _sized(System2ShortRSIThrust, 0.50),
            _sized(System6ShortMeanReversionSixDaySurge, 0.50),
        ]
    if name == "suite7":  # Chapter 10: full suite with the catastrophe hedge
        return [
            _sized(System1LongTrendHighMomentum, 0.25),
            _sized(System4LongTrendLowVolatility, 0.25),
            _sized(System3LongMeanReversionSelloff, 0.25),
            _sized(System5LongMeanReversionADXReversal, 0.25),
            _sized(System2ShortRSIThrust, 0.40),
            _sized(System6ShortMeanReversionSixDaySurge, 0.40),
            _sized(System7CatastropheHedge, 0.20),
        ]
    raise ValueError(
        f"Unknown suite/system {name!r}. "
        f"Use one of: {', '.join(SYSTEM_REGISTRY)} or suite3/suite6/suite7."
    )
