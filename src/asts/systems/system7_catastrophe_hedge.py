"""System 7 — The Catastrophe Hedge.

Long-term trend-following *short* on the SPY only. Goes short on a fresh 50-day
closing low and stays short until a 70-day closing high. It is a net loser on a
bullish backtest by design — it is insurance against 1929/1987/2008-style
down-momentum regimes where the mean-reversion shorts have no setups.

Sizing differs from the other systems: because it is a single instrument the
book allocates a flat percentage of equity (percent-size), so the default
sizing forces the size cap to bind rather than percent-risk.
"""

from __future__ import annotations

import math

from ..core.system import Bars, CandidateSpec, ExitSpec, TradingSystem
from ..core.types import Direction, OrderType, Position, SizingParams, Style

HEDGE_SYMBOL = "SPY"


class System7CatastropheHedge(TradingSystem):
    name = "S7 Catastrophe Hedge"
    direction = Direction.SHORT
    style = Style.TREND
    trail_pct = None

    def __init__(self, sizing: SizingParams | None = None):
        # Single instrument: size by percent-of-equity (allocation), not risk.
        super().__init__(
            sizing
            or SizingParams(risk_pct=1.0, max_pct_size=1.0, max_positions=1, allocation=1.0)
        )

    def entry_signal(self, b: Bars, i: int) -> CandidateSpec | None:
        if b.symbol != HEDGE_SYMBOL:
            return None
        low50 = b.lowest_close_50[i]
        atr40 = b.atr_40[i]
        if math.isnan(low50) or math.isnan(atr40):
            return None
        # Setup: today's close is the lowest close of the last 50 days.
        if not (b.close[i] <= low50):
            return None
        return CandidateSpec(
            rank_value=0.0,
            order_type=OrderType.MARKET_ON_OPEN,
            stop_atr_mult=3.0,
            atr=atr40,
            reference_price=b.close[i],
        )

    def exit_signal(self, pos: Position, b: Bars, i: int) -> ExitSpec | None:
        high70 = b.highest_close_70[i]
        if math.isnan(high70):
            return None
        # Profit protection: exit once the close is a fresh 70-day high.
        if b.close[i] >= high70:
            return ExitSpec(OrderType.MARKET_ON_OPEN, "hedge_exit")
        return None
