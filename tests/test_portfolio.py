import datetime as dt

from asts.core.portfolio import Portfolio
from asts.core.types import Direction


def test_long_round_trip_accounting():
    pf = Portfolio(100_000)
    pf.open(
        system="S", symbol="X", direction=Direction.LONG, shares=100,
        dt=dt.date(2020, 1, 1), price=10.0, initial_stop=8.0, atr=1.0,
        trail_pct=None, commission=0.0,
    )
    assert pf.cash == 99_000
    assert pf.equity({"X": 10.0}) == 100_000      # mark at entry
    assert pf.equity({"X": 12.0}) == 100_200      # unrealized gain
    trade = pf.close(("S", "X"), dt=dt.date(2020, 1, 5), price=12.0,
                     reason="tp", commission=0.0)
    assert pf.cash == 100_200
    assert trade.pnl == 200
    assert trade.is_winner


def test_short_round_trip_accounting():
    pf = Portfolio(100_000)
    pf.open(
        system="S", symbol="Y", direction=Direction.SHORT, shares=100,
        dt=dt.date(2020, 1, 1), price=20.0, initial_stop=23.0, atr=1.0,
        trail_pct=None, commission=0.0,
    )
    assert pf.cash == 102_000                      # received short proceeds
    assert pf.equity({"Y": 20.0}) == 100_000
    assert pf.equity({"Y": 18.0}) == 100_200       # profit when price drops
    trade = pf.close(("S", "Y"), dt=dt.date(2020, 1, 3), price=18.0,
                     reason="tp", commission=0.0)
    assert pf.cash == 100_200
    assert trade.pnl == 200


def test_commission_reduces_pnl():
    pf = Portfolio(100_000)
    pf.open(system="S", symbol="X", direction=Direction.LONG, shares=100,
            dt=dt.date(2020, 1, 1), price=10.0, initial_stop=8.0, atr=1.0,
            trail_pct=None, commission=1.0)
    trade = pf.close(("S", "X"), dt=dt.date(2020, 1, 2), price=10.0,
                     reason="x", commission=1.0)
    assert trade.pnl == -1.0
