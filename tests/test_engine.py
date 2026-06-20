"""Integration tests on deterministic synthetic data."""

import warnings

import pytest

from asts.backtest import run_backtest
from asts.data.synthetic import make_universe
from asts.systems import build_suite

warnings.filterwarnings("ignore")


@pytest.fixture(scope="module")
def universe():
    return make_universe(n_stocks=25, start="2008-01-01", end="2015-12-31", seed=1)


def test_equity_curve_well_formed(universe):
    out = run_backtest(build_suite("s1"), universe)
    eq = out.equity["total_equity"]
    assert len(eq) > 1000
    assert eq.notna().all()
    assert (eq > 0).all()
    assert out.metrics.starting_equity == 100_000


def test_determinism(universe):
    a = run_backtest(build_suite("suite6"), universe)
    b = run_backtest(build_suite("suite6"), universe)
    assert a.metrics.ending_equity == b.metrics.ending_equity
    assert len(a.trades) == len(b.trades)


def test_trend_system_signature(universe):
    """Trend following: low win rate but win/loss ratio well above 1."""
    out = run_backtest(build_suite("s1"), universe)
    assert out.metrics.num_trades > 10
    assert out.metrics.win_rate_pct < 55
    assert out.metrics.win_loss_ratio > 1.5


def test_mean_reversion_short_duration(universe):
    """System 3 mean-reversion exits within its 3-day window (+1 settle)."""
    out = run_backtest(build_suite("s3"), universe)
    if out.trades:
        assert max(t.bars_held for t in out.trades) <= 4
        reasons = {t.exit_reason for t in out.trades}
        assert reasons <= {"profit_target", "time_exit", "stop_loss"}


def test_diversification_reduces_drawdown(universe):
    """The book's central claim: combining non-correlated systems lowers DD."""
    single = run_backtest(build_suite("s1"), universe)
    suite = run_backtest(build_suite("suite7"), universe)
    assert abs(suite.metrics.max_drawdown_pct) < abs(single.metrics.max_drawdown_pct)
    assert suite.metrics.mar >= single.metrics.mar


def test_short_positions_are_taken(universe):
    out = run_backtest(build_suite("s2"), universe)
    assert out.metrics.num_trades > 0
    from asts.core.types import Direction

    assert all(t.direction is Direction.SHORT for t in out.trades)


def test_slippage_reduces_returns(universe):
    from asts.core.engine import BacktestConfig

    base = run_backtest(build_suite("s1"), universe)
    slipped = run_backtest(
        build_suite("s1"), universe, config=BacktestConfig(slippage_pct=0.005)
    )
    assert slipped.metrics.ending_equity < base.metrics.ending_equity
