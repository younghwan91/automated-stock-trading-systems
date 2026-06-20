"""System 4 — Long Trend Low Volatility.

Trend-following long, deliberately de-correlated from System 1 by selecting
*low* historic-volatility names and ranking by the most oversold (lowest
4-day RSI). Tight initial stop, asymmetric pay-off, 20% trailing stop.
"""

from __future__ import annotations

import math

from ..core.system import Bars, CandidateSpec, ExitSpec, TradingSystem
from ..core.types import Direction, OrderType, Position, SizingParams, Style


class System4LongTrendLowVolatility(TradingSystem):
    name = "S4 Long Trend Low Volatility"
    direction = Direction.LONG
    style = Style.TREND
    trail_pct = 0.20

    def __init__(self, sizing: SizingParams | None = None):
        super().__init__(sizing or SizingParams())

    def market_filter(self, market: Bars, i: int) -> bool:
        # Index uptrend: SPY close above its 200-day SMA.
        return market.close[i] > market.sma_200[i]

    def entry_signal(self, b: Bars, i: int) -> CandidateSpec | None:
        close = b.close[i]
        if not (b.advol_50[i] > 100_000_000):
            return None
        hv = b.hv_100[i]
        if math.isnan(hv) or not (10.0 <= hv <= 40.0):
            return None
        # Setup: stock above its 200-day SMA.
        if not (close > b.sma_200[i]):
            return None
        rsi4 = b.rsi_4[i]
        if math.isnan(rsi4):
            return None
        return CandidateSpec(
            rank_value=-rsi4,  # lowest 4-day RSI (most oversold) preferred
            order_type=OrderType.MARKET_ON_OPEN,
            stop_atr_mult=1.5,
            atr=b.atr_40[i],
            reference_price=close,
        )

    def exit_signal(self, pos: Position, b: Bars, i: int) -> ExitSpec | None:
        return None
