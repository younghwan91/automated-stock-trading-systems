"""Robustness suite: Monte Carlo, sizing sensitivity, and walk-forward.

Run from the repo root:  python examples/robustness.py

Demonstrates the three validation tools a single backtest cannot provide:
how lucky the realised path was, how the sizing lever trades growth for
drawdown, and whether the edge survives out of sample.
"""

from __future__ import annotations

import warnings

from asts.analysis import monte_carlo_equity, walk_forward
from asts.analysis.sensitivity import format_sweep, run_sizing_sweep
from asts.backtest import run_backtest
from asts.data.synthetic import make_universe
from asts.systems import build_suite

warnings.filterwarnings("ignore")


def main() -> None:
    universe = make_universe(n_stocks=30, start="2006-01-01", end="2018-12-31", seed=2)

    print("=" * 64)
    print("1) MONTE CARLO  — distribution of outcomes around the realised path")
    print("=" * 64)
    out = run_backtest(build_suite("suite6"), universe)
    print(f"Realised: CAGR {out.metrics.cagr_pct}%  maxDD {out.metrics.max_drawdown_pct}%\n")
    mc = monte_carlo_equity(out.equity, n_sims=2000, method="block", block=10, seed=1)
    print(mc.summary())

    print("\n" + "=" * 64)
    print("2) SIZING SENSITIVITY  — same rules, different position sizing (Ch. 5)")
    print("=" * 64)
    sweep = run_sizing_sweep(
        "suite6", universe,
        risk_grid=[0.01, 0.02, 0.03, 0.05], size_grid=[0.05, 0.10, 0.20],
    )
    print(format_sweep(sweep))

    print("\n" + "=" * 64)
    print("3) WALK-FORWARD  — optimize risk in-sample, validate out-of-sample")
    print("=" * 64)
    wf = walk_forward("suite6", universe, is_years=4, oos_years=2,
                      risk_grid=[0.01, 0.02, 0.03, 0.05])
    print(wf.summary())


if __name__ == "__main__":
    main()
