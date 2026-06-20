"""System 1 — Long Trend High Momentum.

Trend-following long. Buys the most liquid, highest-momentum names while the
S&P 500 is in an uptrend, then rides them with a wide trailing stop.
"""

from __future__ import annotations

import math

from ..core.system import Bars, CandidateSpec, ExitSpec, TradingSystem
from ..core.types import Direction, OrderType, Position, SizingParams, Style


class System1LongTrendHighMomentum(TradingSystem):
    name = "S1 Long Trend High Momentum"
    direction = Direction.LONG
    style = Style.TREND
    trail_pct = 0.25  # 25% trailing stop (profit protection)

    def __init__(self, sizing: SizingParams | None = None):
        super().__init__(sizing or SizingParams())

    def market_filter(self, market: Bars, i: int) -> bool:
        # Index uptrend: SPY close above its 100-day SMA.
        return market.close[i] > market.sma_100[i]

    def entry_signal(self, b: Bars, i: int) -> CandidateSpec | None:
        close = b.close[i]
        # Filter: liquidity + minimum price.
        if not (b.advol_20[i] > 50_000_000 and close >= 5.0):
            return None
        # Setup: simple stock uptrend, 25-SMA above 50-SMA.
        if not (b.sma_25[i] > b.sma_50[i]):
            return None
        rank = b.roc_200[i]  # highest 200-day rate of change preferred
        if math.isnan(rank):
            return None
        return CandidateSpec(
            rank_value=rank,
            order_type=OrderType.MARKET_ON_OPEN,
            stop_atr_mult=5.0,
            atr=b.atr_20[i],
            reference_price=close,
        )

    def exit_signal(self, pos: Position, b: Bars, i: int) -> ExitSpec | None:
        # No profit target / time stop: managed by ATR stop + 25% trailing stop.
        return None
