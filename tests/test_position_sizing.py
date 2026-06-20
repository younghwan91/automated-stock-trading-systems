import pytest

from asts.core.position_sizing import calculate_shares, stop_distance
from asts.core.types import SizingParams


def test_book_example_size_cap_binds():
    """Book's worked example: $100k equity, $30 stock, ATR $2, 2x ATR stop.

    Percent-risk wants 500 shares ($2,000 / $4) but the 10% size cap limits the
    position to 333 shares ($10,000 / $30). The smaller wins.
    """
    params = SizingParams(risk_pct=0.02, max_pct_size=0.10, allocation=1.0)
    shares = calculate_shares(
        total_equity=100_000,
        reference_price=30.0,
        atr=2.0,
        stop_atr_mult=2.0,
        params=params,
    )
    assert shares == 333


def test_percent_risk_binds_for_volatile_stock():
    """A wide stop makes percent-risk the binding constraint (< size cap)."""
    params = SizingParams(risk_pct=0.02, max_pct_size=0.10)
    # stop distance = 5 * 4 = $20 per share -> 2000/20 = 100 shares (risk)
    # size cap = 10000/30 = 333 shares -> risk binds
    shares = calculate_shares(
        total_equity=100_000, reference_price=30.0, atr=4.0,
        stop_atr_mult=5.0, params=params,
    )
    assert shares == 100


def test_allocation_scales_capital():
    full = calculate_shares(
        total_equity=100_000, reference_price=30.0, atr=2.0, stop_atr_mult=2.0,
        params=SizingParams(allocation=1.0),
    )
    half = calculate_shares(
        total_equity=100_000, reference_price=30.0, atr=2.0, stop_atr_mult=2.0,
        params=SizingParams(allocation=0.5),
    )
    assert half == full // 2


def test_zero_reference_price_is_safe():
    assert calculate_shares(
        total_equity=100_000, reference_price=0.0, atr=2.0, stop_atr_mult=2.0,
        params=SizingParams(),
    ) == 0


def test_stop_distance():
    assert stop_distance(30.0, 2.0, 2.0) == pytest.approx(4.0)
