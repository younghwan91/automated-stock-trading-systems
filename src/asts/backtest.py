"""High-level convenience API: data in, results out.

``run_backtest`` takes a raw ``{symbol: OHLCV DataFrame}`` universe, computes the
feature set, runs the engine and returns the equity curve (as a DataFrame), the
trade ledger and a :class:`~asts.metrics.Metrics` summary.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .core.engine import BacktestConfig, BacktestEngine
from .core.system import TradingSystem
from .data.features import compute_features, to_bars
from .metrics import Metrics, compute_metrics


@dataclass
class RunOutput:
    equity: pd.DataFrame
    trades: list
    metrics: Metrics
    portfolio: object


def build_bars(universe: dict[str, pd.DataFrame]) -> dict:
    """Compute features and convert every symbol to a :class:`Bars` object."""
    bars = {}
    for sym, df in universe.items():
        bars[sym] = to_bars(sym, compute_features(df))
    return bars


def equity_dataframe(portfolio) -> pd.DataFrame:
    rows = [
        {
            "date": p.dt,
            "total_equity": p.total_equity,
            "cash": p.cash,
            "long_exposure": p.long_exposure,
            "short_exposure": p.short_exposure,
            "open_positions": p.open_positions,
        }
        for p in portfolio.equity_curve
    ]
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")


def run_backtest(
    systems: list[TradingSystem],
    universe: dict[str, pd.DataFrame],
    market_symbol: str = "SPY",
    config: BacktestConfig | None = None,
) -> RunOutput:
    bars = build_bars(universe)
    engine = BacktestEngine(systems, bars, market_symbol=market_symbol, config=config)
    portfolio = engine.run()

    equity = equity_dataframe(portfolio)
    benchmark = universe[market_symbol]["close"].copy()
    benchmark.index = pd.to_datetime(benchmark.index)
    metrics = compute_metrics(equity, portfolio.closed_trades, benchmark=benchmark)
    return RunOutput(
        equity=equity,
        trades=portfolio.closed_trades,
        metrics=metrics,
        portfolio=portfolio,
    )
