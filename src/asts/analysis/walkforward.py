"""Walk-forward optimization and out-of-sample validation.

A backtest that tunes parameters on the same data it reports is worthless. Here
we tune the one lever the book treats as primary — percent-risk — on a rolling
*in-sample* window, then measure performance on the immediately following
*out-of-sample* window the optimiser never saw. Stitching the OOS windows yields
an honest, optimisation-bias-free equity path.

For comparison we also run a fixed default (risk = 2%) over the same OOS windows;
if walk-forward optimization barely beats the fixed default, the edge is in the
systems, not in curve-fitting the lever — which is the desirable outcome.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import pandas as pd

from ..backtest import run_backtest
from ..core.engine import BacktestConfig
from ..systems import build_suite


@dataclass
class WalkForwardResult:
    folds: pd.DataFrame
    combined_oos_return_pct: float
    combined_oos_cagr_pct: float
    avg_oos_mar: float
    default_combined_oos_return_pct: float
    objective: str = "mar"

    def summary(self) -> str:
        return (
            f"Walk-Forward ({len(self.folds)} OOS folds, objective={self.objective})\n"
            + "-" * 60 + "\n"
            + self.folds.round(2).to_string(index=False)
            + "\n\n"
            + f"Combined OOS return (optimized) : {self.combined_oos_return_pct:.2f}%\n"
            + f"Combined OOS return (fixed 2%)  : {self.default_combined_oos_return_pct:.2f}%\n"
            + f"Combined OOS CAGR (optimized)   : {self.combined_oos_cagr_pct:.2f}%\n"
            + f"Average OOS MAR                 : {self.avg_oos_mar:.2f}"
        )


def _suite_with_risk(suite_name: str, risk_pct: float):
    systems = build_suite(suite_name)
    for s in systems:
        s.sizing = replace(s.sizing, risk_pct=risk_pct)
    return systems


def _run_window(suite_name, universe, market_symbol, risk, start, end, equity):
    cfg = BacktestConfig(starting_equity=equity, trade_start=start, trade_end=end)
    systems = _suite_with_risk(suite_name, risk)
    return run_backtest(systems, universe, market_symbol=market_symbol, config=cfg)


def walk_forward(
    suite_name: str,
    universe: dict,
    market_symbol: str = "SPY",
    is_years: float = 4.0,
    oos_years: float = 2.0,
    risk_grid: list[float] = (0.005, 0.01, 0.02, 0.03, 0.05),
    objective: str = "mar",
    starting_equity: float = 100_000.0,
) -> WalkForwardResult:
    """Roll IS/OOS windows across the data, optimizing ``risk_pct`` each fold."""
    dates = pd.to_datetime(universe[market_symbol].index)
    t0, t1 = dates.min(), dates.max()

    folds = []
    opt_equity = starting_equity
    def_equity = starting_equity
    opt_compound = 1.0
    def_compound = 1.0
    mar_sum = 0.0

    is_start = t0
    while True:
        is_end = is_start + pd.DateOffset(years=is_years)
        oos_end = is_end + pd.DateOffset(years=oos_years)
        if is_end >= t1:
            break
        oos_end = min(oos_end, t1)

        is_s, is_e = is_start.date(), is_end.date()
        oos_s, oos_e = is_end.date(), oos_end.date()

        # In-sample: pick the risk level that maximises the objective.
        best_risk, best_obj = risk_grid[len(risk_grid) // 2], -1e18
        for risk in risk_grid:
            out = _run_window(suite_name, universe, market_symbol, risk, is_s, is_e, starting_equity)
            val = getattr(out.metrics, "mar" if objective == "mar" else "cagr_pct")
            if val > best_obj:
                best_obj, best_risk = val, risk

        # Out-of-sample: apply the chosen risk, and a fixed-2% baseline.
        oos = _run_window(suite_name, universe, market_symbol, best_risk, oos_s, oos_e, opt_equity)
        base = _run_window(suite_name, universe, market_symbol, 0.02, oos_s, oos_e, def_equity)

        opt_ret = oos.metrics.total_return_pct / 100.0
        def_ret = base.metrics.total_return_pct / 100.0
        opt_compound *= 1.0 + opt_ret
        def_compound *= 1.0 + def_ret
        opt_equity = oos.metrics.ending_equity
        def_equity = base.metrics.ending_equity
        mar_sum += oos.metrics.mar

        folds.append(
            {
                "is_start": is_s, "is_end": is_e, "oos_end": oos_e,
                "chosen_risk_pct": best_risk * 100,
                "oos_cagr_pct": oos.metrics.cagr_pct,
                "oos_maxdd_pct": oos.metrics.max_drawdown_pct,
                "oos_mar": oos.metrics.mar,
                "oos_return_pct": oos.metrics.total_return_pct,
                "fixed2pct_return_pct": base.metrics.total_return_pct,
            }
        )
        is_start = is_start + pd.DateOffset(years=oos_years)

    if not folds:
        raise ValueError("data span too short for the requested IS/OOS windows")

    folds_df = pd.DataFrame(folds)
    n_oos = len(folds)
    total_oos_years = n_oos * oos_years
    combined_cagr = (opt_compound ** (1.0 / max(total_oos_years, 1e-9)) - 1.0) * 100.0

    return WalkForwardResult(
        folds=folds_df,
        combined_oos_return_pct=(opt_compound - 1.0) * 100.0,
        combined_oos_cagr_pct=combined_cagr,
        avg_oos_mar=mar_sum / n_oos,
        default_combined_oos_return_pct=(def_compound - 1.0) * 100.0,
        objective=objective,
    )
