"""ASTS — Automated Stock Trading Systems.

A research-grade backtesting engine implementing the seven non-correlated
trading systems described in Laurens Bensdorp's *Automated Stock Trading
Systems* (2020). Educational/research use only — not investment advice.
"""

from __future__ import annotations

from .backtest import RunOutput, run_backtest
from .core.engine import BacktestConfig, BacktestEngine
from .core.types import Direction, SizingParams, Style
from .metrics import Metrics, compute_metrics, format_metrics
from .systems import SYSTEM_REGISTRY, build_suite

__version__ = "0.1.0"

__all__ = [
    "run_backtest",
    "RunOutput",
    "BacktestEngine",
    "BacktestConfig",
    "build_suite",
    "SYSTEM_REGISTRY",
    "compute_metrics",
    "format_metrics",
    "Metrics",
    "Direction",
    "Style",
    "SizingParams",
    "__version__",
]
