"""System 2 — Short RSI Thrust.

Short mean reversion. Shorts over-extended names (3-day RSI > 90, two rising
closes) via a limit 4% above the prior close, capturing intraday greed. Exits
on a 4% profit or after 2 days. Negatively correlated with the long book.
"""

from __future__ import annotations

import math

from ..core.system import Bars, CandidateSpec, ExitSpec, TradingSystem
from ..core.types import Direction, OrderType, Position, SizingParams, Style


class System2ShortRSIThrust(TradingSystem):
    name = "S2 Short RSI Thrust"
    direction = Direction.SHORT
    style = Style.MEAN_REVERSION
    trail_pct = None

    LIMIT_ABOVE = 0.04
    PROFIT_TARGET = 0.04
    MAX_DAYS = 2

    def __init__(self, sizing: SizingParams | None = None):
        super().__init__(sizing or SizingParams())

    def entry_signal(self, b: Bars, i: int) -> CandidateSpec | None:
        if i < 2:
            return None
        close = b.close[i]
        if not (close >= 5.0 and b.advol_20[i] > 25_000_000 and b.atrp_10[i] >= 3.0):
            return None
        rsi3 = b.rsi_3[i]
        adx7 = b.adx_7[i]
        if math.isnan(rsi3) or math.isnan(adx7):
            return None
        # Setup: extreme overbought + two consecutive higher closes.
        two_up = b.close[i] > b.close[i - 1] and b.close[i - 1] > b.close[i - 2]
        if not (rsi3 > 90.0 and two_up):
            return None
        limit_price = close * (1.0 + self.LIMIT_ABOVE)
        return CandidateSpec(
            rank_value=adx7,  # highest 7-day ADX preferred
            order_type=OrderType.LIMIT,
            stop_atr_mult=3.0,
            atr=b.atr_10[i],
            reference_price=limit_price,
            limit_price=limit_price,
        )

    def exit_signal(self, pos: Position, b: Bars, i: int) -> ExitSpec | None:
        gain = (pos.entry_price - b.close[i]) / pos.entry_price  # short P&L
        if gain >= self.PROFIT_TARGET:
            return ExitSpec(OrderType.MARKET_ON_CLOSE, "profit_target")
        if pos.bars_held >= self.MAX_DAYS:
            return ExitSpec(OrderType.MARKET_ON_CLOSE, "time_exit")
        return None
