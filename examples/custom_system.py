"""Extending the framework: an 8th system in ~20 lines.

`System8 Long Donchian Breakout` is a classic trend-following long: enter on a
new 50-day closing high while the market is in an uptrend, ride it with a 3x ATR
stop and a 20% trailing stop. The engine handles sizing, stops and accounting —
a new system only declares its entry/exit logic.

Run from the repo root:  python examples/custom_system.py
"""

from __future__ import annotations

import math
import warnings

import numpy as np

from asts.backtest import run_backtest
from asts.core.system import Bars, CandidateSpec, ExitSpec, TradingSystem
from asts.core.types import Direction, OrderType, Position, SizingParams, Style
from asts.data.synthetic import make_universe
from asts.metrics import format_metrics

warnings.filterwarnings("ignore")


class System8LongDonchianBreakout(TradingSystem):
    name = "S8 Long Donchian Breakout"
    direction = Direction.LONG
    style = Style.TREND
    trail_pct = 0.20
    LOOKBACK = 50

    def market_filter(self, market: Bars, i: int) -> bool:
        # Trade breakouts only while SPY is above its 100-day SMA.
        return market.close[i] > market.sma_100[i]

    def entry_signal(self, b: Bars, i: int) -> CandidateSpec | None:
        if i < self.LOOKBACK:
            return None
        close = b.close[i]
        if not (b.advol_20[i] > 25_000_000 and close >= 5.0):
            return None
        window = b.close[i - self.LOOKBACK + 1 : i + 1]
        # New 50-day closing high == breakout.
        if not (close >= np.nanmax(window)):
            return None
        atr20 = b.atr_20[i]
        if math.isnan(atr20):
            return None
        return CandidateSpec(
            rank_value=b.roc_200[i],  # prefer strongest longer-term momentum
            order_type=OrderType.MARKET_ON_OPEN,
            stop_atr_mult=3.0,
            atr=atr20,
            reference_price=close,
        )

    def exit_signal(self, pos: Position, b: Bars, i: int) -> ExitSpec | None:
        return None  # managed entirely by the ATR + trailing stop


def main() -> None:
    universe = make_universe(n_stocks=40, start="2008-01-01", end="2018-12-31", seed=3)
    systems = [System8LongDonchianBreakout(SizingParams(allocation=1.0))]
    out = run_backtest(systems, universe)
    print(format_metrics(out.metrics))
    print(f"\nClosed trades: {len(out.trades)}")


if __name__ == "__main__":
    main()
