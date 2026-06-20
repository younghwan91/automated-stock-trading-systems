"""System 5 — Long Mean Reversion High ADX Reversal.

Buys moderate pullbacks (3-day RSI < 50) inside strong trends (7-day ADX > 55,
close above 100-SMA + 1 ATR), with a limit 3% below the prior close. Exits on a
1-ATR profit or after 6 days.
"""

from __future__ import annotations

import math

from ..core.system import Bars, CandidateSpec, ExitSpec, TradingSystem
from ..core.types import Direction, OrderType, Position, SizingParams, Style


class System5LongMeanReversionADXReversal(TradingSystem):
    name = "S5 Long Mean Reversion High ADX Reversal"
    direction = Direction.LONG
    style = Style.MEAN_REVERSION
    trail_pct = None

    LIMIT_BELOW = 0.03
    MAX_DAYS = 6

    def __init__(self, sizing: SizingParams | None = None):
        super().__init__(sizing or SizingParams())

    def entry_signal(self, b: Bars, i: int) -> CandidateSpec | None:
        close = b.close[i]
        if not (
            b.avgvol_50[i] >= 500_000
            and b.advol_50[i] >= 2_500_000
            and b.atrp_10[i] > 4.0
        ):
            return None
        atr10 = b.atr_10[i]
        adx7 = b.adx_7[i]
        rsi3 = b.rsi_3[i]
        if math.isnan(atr10) or math.isnan(adx7) or math.isnan(rsi3):
            return None
        # Setup: significant uptrend + strength + moderate pullback.
        if not (close > b.sma_100[i] + atr10 and adx7 > 55.0 and rsi3 < 50.0):
            return None
        limit_price = close * (1.0 - self.LIMIT_BELOW)
        return CandidateSpec(
            rank_value=adx7,  # highest 7-day ADX preferred
            order_type=OrderType.LIMIT,
            stop_atr_mult=3.0,
            atr=atr10,
            reference_price=limit_price,
            limit_price=limit_price,
        )

    def exit_signal(self, pos: Position, b: Bars, i: int) -> ExitSpec | None:
        # Profit target of one ATR (captured at entry), then exit next open.
        if (b.close[i] - pos.entry_price) >= pos.atr_at_entry:
            return ExitSpec(OrderType.MARKET_ON_OPEN, "profit_target")
        if pos.bars_held >= self.MAX_DAYS:
            return ExitSpec(OrderType.MARKET_ON_OPEN, "time_exit")
        return None
