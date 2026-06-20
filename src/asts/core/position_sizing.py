"""Position sizing — the most important lever in the book.

Bensdorp combines two constraints and takes the *smaller* resulting size:

1. **Percent-risk**: risk a fixed fraction of equity per trade. The dollar
   risk per share is the distance between entry and the protective stop, so

       shares_risk = (risk_pct * system_equity) / stop_distance_per_share

2. **Percent-size**: never let a single position exceed a fixed fraction of
   equity (protects against gap risk when the stop is very tight)

       shares_size = (max_pct_size * system_equity) / reference_price

The final size is ``min(shares_risk, shares_size)`` floored to a whole number.

``system_equity`` is ``total_equity * allocation`` so the same logic works for
a single system (allocation = 1.0) and for a multi-system suite where each
system is assigned a slice of capital.
"""

from __future__ import annotations

import math

from .types import SizingParams


def stop_distance(reference_price: float, atr: float, stop_atr_mult: float) -> float:
    """Per-share distance between entry and the ATR-based protective stop."""
    return abs(stop_atr_mult * atr)


def calculate_shares(
    *,
    total_equity: float,
    reference_price: float,
    atr: float,
    stop_atr_mult: float,
    params: SizingParams,
) -> int:
    """Return the number of shares to trade (>= 0).

    ``reference_price`` is the price used for the percent-size cap: the limit
    price for limit orders, or the last close as a proxy for market orders.
    """
    if reference_price <= 0.0:
        return 0

    system_equity = total_equity * params.allocation
    dollar_risk = params.risk_pct * system_equity
    per_share_risk = stop_distance(reference_price, atr, stop_atr_mult)

    if per_share_risk <= 0.0:
        shares_risk = math.inf
    else:
        shares_risk = dollar_risk / per_share_risk

    max_position_value = params.max_pct_size * system_equity
    shares_size = max_position_value / reference_price

    shares = int(math.floor(min(shares_risk, shares_size)))
    return max(shares, 0)
