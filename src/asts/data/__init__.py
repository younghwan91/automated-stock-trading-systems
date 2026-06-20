"""Data providers: synthetic (offline) and yfinance (optional, real data)."""

from __future__ import annotations

from .synthetic import make_universe

__all__ = ["make_universe"]
