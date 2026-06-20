"""Compare each system individually against the combined suites.

Run from the repo root:  python examples/run_suite.py
Demonstrates the book's central thesis — combining non-correlated systems
lowers drawdown and raises risk-adjusted return (MAR/Sharpe).
"""

from __future__ import annotations

import warnings

from asts.backtest import run_backtest
from asts.data.synthetic import make_universe
from asts.systems import build_suite

warnings.filterwarnings("ignore")


def main() -> None:
    universe = make_universe(n_stocks=40, start="2006-01-01", end="2018-12-31", seed=2)

    names = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "suite3", "suite6", "suite7"]
    header = f"{'strategy':<10}{'CAGR%':>8}{'MaxDD%':>9}{'MAR':>7}{'Sharpe':>8}{'Trades':>8}{'Corr':>8}"
    print(header)
    print("-" * len(header))
    for name in names:
        out = run_backtest(build_suite(name), universe)
        m = out.metrics
        print(
            f"{name:<10}{m.cagr_pct:>8.2f}{m.max_drawdown_pct:>9.2f}"
            f"{m.mar:>7.2f}{m.sharpe:>8.2f}{m.num_trades:>8d}{m.benchmark_corr:>8.3f}"
        )


if __name__ == "__main__":
    main()
