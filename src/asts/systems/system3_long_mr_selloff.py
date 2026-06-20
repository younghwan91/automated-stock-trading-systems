"""System 3 — Long Mean Reversion Selloff.

Buys sharp pullbacks (>=12.5% drop over 3 days) in stocks that are still above
their 150-day SMA, using a limit order 7% below the prior close ("buying a
falling knife"). Exits on a 4% profit or after 3 days.
"""

from __future__ import annotations

import math

from ..core.system import Bars, CandidateSpec, ExitSpec, TradingSystem
from ..core.types import Direction, OrderType, Position, SizingParams, Style


class System3LongMeanReversionSelloff(TradingSystem):
    name = "S3 Long Mean Reversion Selloff"
    direction = Direction.LONG
    style = Style.MEAN_REVERSION
    trail_pct = None

    LIMIT_BELOW = 0.07
    PROFIT_TARGET = 0.04
    MAX_DAYS = 3

    def __init__(self, sizing: SizingParams | None = None):
        super().__init__(sizing or SizingParams())

    def entry_signal(self, b: Bars, i: int) -> CandidateSpec | None:
        close = b.close[i]
        if not (close >= 1.0 and b.avgvol_50[i] >= 1_000_000 and b.atrp_10[i] >= 5.0):
            return None
        # Setup: uptrend (above 150-SMA) but a >=12.5% three-day selloff.
        ret3 = b.ret_3[i]
        if math.isnan(ret3):
            return None
        if not (close > b.sma_150[i] and ret3 <= -0.125):
            return None
        limit_price = close * (1.0 - self.LIMIT_BELOW)
        return CandidateSpec(
            rank_value=-ret3,  # biggest drop preferred
            order_type=OrderType.LIMIT,
            stop_atr_mult=2.5,
            atr=b.atr_10[i],
            reference_price=limit_price,
            limit_price=limit_price,
        )

    def exit_signal(self, pos: Position, b: Bars, i: int) -> ExitSpec | None:
        gain = (b.close[i] - pos.entry_price) / pos.entry_price
        if gain >= self.PROFIT_TARGET:
            return ExitSpec(OrderType.MARKET_ON_CLOSE, "profit_target")
        if pos.bars_held >= self.MAX_DAYS:
            return ExitSpec(OrderType.MARKET_ON_CLOSE, "time_exit")
        return None
