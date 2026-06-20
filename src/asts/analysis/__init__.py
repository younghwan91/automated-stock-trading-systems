"""Robustness & validation: Monte Carlo, walk-forward, sizing sensitivity.

These tools answer the questions a single backtest cannot: *how lucky was this
path?* (Monte Carlo), *does the edge survive out of sample?* (walk-forward), and
*how does the position-sizing lever trade growth for drawdown?* (sensitivity) —
the latter being the central message of the book's Chapter 5.
"""

from __future__ import annotations

from .montecarlo import MonteCarloResult, monte_carlo_equity
from .sensitivity import run_sizing_sweep
from .walkforward import WalkForwardResult, walk_forward

__all__ = [
    "monte_carlo_equity",
    "MonteCarloResult",
    "run_sizing_sweep",
    "walk_forward",
    "WalkForwardResult",
]
