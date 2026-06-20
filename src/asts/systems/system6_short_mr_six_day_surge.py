"""System 6 — Short Mean Reversion High Six-Day Surge.

A second short mean-reversion system, de-correlated from System 2. Shorts names
up >=20% over six days (with two rising closes) via a limit 5% above the prior
close. Exits on a 5% profit or after 3 days.
"""

from __future__ import annotations

import math

from ..core.system import Bars, CandidateSpec, ExitSpec, TradingSystem
from ..core.types import Direction, OrderType, Position, SizingParams, Style


class System6ShortMeanReversionSixDaySurge(TradingSystem):
    name = "S6 Short Mean Reversion High Six-Day Surge"
    direction = Direction.SHORT
    style = Style.MEAN_REVERSION
    trail_pct = None

    LIMIT_ABOVE = 0.05
    PROFIT_TARGET = 0.05
    MAX_DAYS = 3

    def __init__(self, sizing: SizingParams | None = None):
        super().__init__(sizing or SizingParams())

    def entry_signal(self, b: Bars, i: int) -> CandidateSpec | None:
        if i < 2:
            return None
        close = b.close[i]
        if not (close >= 5.0 and b.advol_50[i] >= 10_000_000):
            return None
        ret6 = b.ret_6[i]
        if math.isnan(ret6):
            return None
        two_up = b.close[i] > b.close[i - 1] and b.close[i - 1] > b.close[i - 2]
        if not (ret6 >= 0.20 and two_up):
            return None
        limit_price = close * (1.0 + self.LIMIT_ABOVE)
        return CandidateSpec(
            rank_value=ret6,  # biggest six-day surge preferred
            order_type=OrderType.LIMIT,
            stop_atr_mult=3.0,
            atr=b.atr_10[i],
            reference_price=limit_price,
            limit_price=limit_price,
        )

    def exit_signal(self, pos: Position, b: Bars, i: int) -> ExitSpec | None:
        gain = (pos.entry_price - b.close[i]) / pos.entry_price
        if gain >= self.PROFIT_TARGET:
            return ExitSpec(OrderType.MARKET_ON_CLOSE, "profit_target")
        if pos.bars_held >= self.MAX_DAYS:
            return ExitSpec(OrderType.MARKET_ON_CLOSE, "time_exit")
        return None
