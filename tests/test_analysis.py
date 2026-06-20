"""Tests for the robustness layer: Monte Carlo, sizing sweep, walk-forward."""

import datetime as dt
import warnings

import numpy as np
import pandas as pd
import pytest

from asts.analysis import monte_carlo_equity, run_sizing_sweep, walk_forward
from asts.backtest import run_backtest
from asts.core.engine import BacktestConfig
from asts.data.synthetic import make_universe
from asts.systems import build_suite

warnings.filterwarnings("ignore")


@pytest.fixture(scope="module")
def universe():
    return make_universe(n_stocks=20, start="2006-01-01", end="2016-12-31", seed=2)


# --- Monte Carlo -----------------------------------------------------------
def _equity_curve(cagr=0.10, days=2520, vol=0.01, seed=0):
    rng = np.random.default_rng(seed)
    mu = (1 + cagr) ** (1 / 252) - 1
    rets = rng.normal(mu, vol, days)
    eq = 100_000 * np.cumprod(1 + rets)
    idx = pd.bdate_range("2010-01-01", periods=days)
    return pd.DataFrame({"total_equity": eq}, index=idx)


def test_monte_carlo_shapes_and_bounds():
    eq = _equity_curve(seed=1)
    mc = monte_carlo_equity(eq, n_sims=500, method="block", block=10, seed=0)
    assert mc.cagr.shape == (500,)
    assert (mc.max_drawdown <= 0).all()
    p = mc.percentiles()
    assert p.loc["cagr_pct", "p5"] <= p.loc["cagr_pct", "p95"]


def test_monte_carlo_probabilities_in_range():
    eq = _equity_curve(seed=2)
    mc = monte_carlo_equity(eq, n_sims=400, method="iid", seed=0)
    assert 0.0 <= mc.prob_drawdown_worse_than(20) <= 1.0
    assert 0.0 <= mc.prob_negative_return() <= 1.0


def test_monte_carlo_rejects_unknown_method():
    eq = _equity_curve()
    with pytest.raises(ValueError):
        monte_carlo_equity(eq, n_sims=10, method="bogus")


def test_monte_carlo_is_deterministic_with_seed():
    eq = _equity_curve(seed=3)
    a = monte_carlo_equity(eq, n_sims=200, seed=42)
    b = monte_carlo_equity(eq, n_sims=200, seed=42)
    assert np.allclose(a.cagr, b.cagr)


# --- Sizing sensitivity ----------------------------------------------------
def test_sizing_sweep_monotonic_drawdown(universe):
    """The book's thesis: bigger size cap => bigger drawdown (rules unchanged)."""
    df = run_sizing_sweep(
        "suite6", universe, risk_grid=[0.02], size_grid=[0.05, 0.10, 0.20]
    )
    dd = df.sort_values("max_pct_size")["max_drawdown_pct"].to_numpy()
    # drawdowns get deeper (more negative) as the size cap grows
    assert dd[0] >= dd[1] >= dd[2]


def test_sizing_sweep_grid_shape(universe):
    df = run_sizing_sweep(
        "s1", universe, risk_grid=[0.01, 0.02], size_grid=[0.10, 0.20]
    )
    assert len(df) == 4
    assert {"cagr_pct", "max_drawdown_pct", "mar"} <= set(df.columns)


# --- Engine trade window (walk-forward primitive) --------------------------
def test_trade_window_restricts_dates(universe):
    cfg = BacktestConfig(trade_start=dt.date(2012, 1, 1), trade_end=dt.date(2013, 12, 31))
    out = run_backtest(build_suite("s1"), universe, config=cfg)
    idx = out.equity.index
    assert idx.min() >= pd.Timestamp("2012-01-01")
    assert idx.max() <= pd.Timestamp("2013-12-31")


# --- Walk-forward ----------------------------------------------------------
def test_walk_forward_runs_and_reports(universe):
    wf = walk_forward(
        "s1", universe, is_years=4, oos_years=2, risk_grid=[0.01, 0.02, 0.05]
    )
    assert len(wf.folds) >= 2
    assert {"chosen_risk_pct", "oos_mar", "oos_return_pct"} <= set(wf.folds.columns)
    # chosen risk always comes from the grid
    assert set(wf.folds["chosen_risk_pct"]) <= {1.0, 2.0, 5.0}
