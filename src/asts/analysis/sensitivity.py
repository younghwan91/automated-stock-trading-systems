"""Position-sizing sensitivity — the book's central Chapter 5 demonstration.

"Through position sizing we can completely change the returns ... with the exact
same buy and sell decisions." This sweep keeps the buy/sell logic fixed and
varies only the percent-risk and percent-size levers, tabulating how CAGR and
maximum drawdown move together. Conservative sizing buys a smaller drawdown at
the cost of CAGR; aggressive sizing does the opposite.
"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from ..backtest import run_backtest
from ..core.engine import BacktestConfig
from ..systems import build_suite


def _suite_with_sizing(suite_name: str, risk_pct: float, max_pct_size: float):
    """Rebuild a suite, overriding the sizing levers but keeping allocations."""
    systems = build_suite(suite_name)
    for s in systems:
        s.sizing = replace(s.sizing, risk_pct=risk_pct, max_pct_size=max_pct_size)
    return systems


def run_sizing_sweep(
    suite_name: str,
    universe: dict,
    risk_grid: list[float] = (0.005, 0.01, 0.02, 0.03, 0.05),
    size_grid: list[float] = (0.05, 0.10, 0.20),
    market_symbol: str = "SPY",
    config: BacktestConfig | None = None,
) -> pd.DataFrame:
    """Return a tidy DataFrame of metrics over the (risk_pct × max_pct_size) grid."""
    base = config or BacktestConfig()
    rows = []
    for risk in risk_grid:
        for size in size_grid:
            systems = _suite_with_sizing(suite_name, risk, size)
            out = run_backtest(systems, universe, market_symbol=market_symbol, config=base)
            m = out.metrics
            rows.append(
                {
                    "risk_pct": risk,
                    "max_pct_size": size,
                    "cagr_pct": m.cagr_pct,
                    "max_drawdown_pct": m.max_drawdown_pct,
                    "mar": m.mar,
                    "sharpe": m.sharpe,
                    "volatility_pct": m.volatility_pct,
                    "trades": m.num_trades,
                }
            )
    return pd.DataFrame(rows)


def format_sweep(df: pd.DataFrame) -> str:
    """Pretty CAGR / MaxDD pivot tables for quick reading."""
    cagr = df.pivot(index="risk_pct", columns="max_pct_size", values="cagr_pct")
    dd = df.pivot(index="risk_pct", columns="max_pct_size", values="max_drawdown_pct")
    return (
        "CAGR % by (risk_pct rows × max_pct_size cols)\n"
        + cagr.round(2).to_string()
        + "\n\nMax Drawdown % by (risk_pct rows × max_pct_size cols)\n"
        + dd.round(2).to_string()
    )
