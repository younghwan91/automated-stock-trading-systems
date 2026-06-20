"""Smoke test for the optional tear-sheet plotting (headless Agg backend)."""

import warnings

import pytest

from asts.backtest import run_backtest
from asts.data.synthetic import make_universe
from asts.systems import build_suite

warnings.filterwarnings("ignore")

pytest.importorskip("matplotlib")


def test_tearsheet_saves_png(tmp_path):
    from asts.plotting import plot_tearsheet

    universe = make_universe(n_stocks=12, start="2010-01-01", end="2013-12-31", seed=4)
    out = run_backtest(build_suite("suite3"), universe)
    target = tmp_path / "tearsheet.png"
    fig = plot_tearsheet(
        out.equity,
        benchmark=universe["SPY"]["close"],
        savepath=str(target),
        show=False,
    )
    assert target.exists()
    assert target.stat().st_size > 0
    assert len(fig.axes) == 3
