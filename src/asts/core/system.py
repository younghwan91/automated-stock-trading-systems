"""The 12-ingredient trading-system abstraction.

Every system in the book is described by the same twelve ingredients
(objective, beliefs, universe, filter, setup, ranking, entry, stop-loss,
re-entry, profit protection, profit taking, position sizing). This module
turns that template into a small, strongly-typed interface that the backtest
engine can drive uniformly.

A concrete system answers three questions for the engine:

* ``market_filter`` — is the *index* regime right to take new trades today?
* ``entry_signal``  — given one symbol's history up to bar ``i``, is there a
  setup, and if so what order should be placed tomorrow and how should it be
  sized/stopped?
* ``exit_signal``   — given an open position, should a market exit be
  scheduled for tomorrow (profit target / time stop)?

Intraday protective exits (ATR stop-loss, trailing stop) are handled centrally
by the engine from the :class:`Position` fields, because they are mechanical
and identical in structure across systems.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .types import Direction, OrderType, Position, SizingParams, Style


@dataclass(slots=True)
class CandidateSpec:
    """A setup detected at the close of bar ``i`` for execution next bar."""

    rank_value: float          # higher = preferred when slots are scarce
    order_type: OrderType
    stop_atr_mult: float
    atr: float                 # ATR captured at signal (drives stop + sizing)
    reference_price: float     # for sizing (limit price or last close)
    limit_price: float | None = None


@dataclass(slots=True)
class ExitSpec:
    order_type: OrderType      # MOO or MOC
    reason: str


class Bars:
    """Column-oriented view over one symbol's OHLCV + indicator arrays.

    Access columns as attributes (``b.close``, ``b.rsi_3`` ...). Each is a
    NumPy array aligned to ``b.dates``. Systems index by integer bar ``i``.
    """

    __slots__ = ("symbol", "dates", "cols")

    def __init__(self, symbol: str, dates, cols: dict):
        self.symbol = symbol
        self.dates = dates
        self.cols = cols

    def __getattr__(self, name):
        try:
            return self.cols[name]
        except KeyError as exc:  # pragma: no cover - defensive
            raise AttributeError(name) from exc

    def __len__(self) -> int:
        return len(self.dates)


class TradingSystem(ABC):
    """Base class for all seven systems."""

    name: str = "unnamed"
    direction: Direction = Direction.LONG
    style: Style = Style.TREND
    trail_pct: float | None = None  # trailing-stop fraction, or None

    def __init__(self, sizing: SizingParams | None = None):
        self.sizing = sizing or SizingParams()

    # --- market regime ---------------------------------------------------
    def market_filter(self, market: Bars, i: int) -> bool:
        """Default: no index dependency (always tradable)."""
        return True

    # --- entry -----------------------------------------------------------
    @abstractmethod
    def entry_signal(self, b: Bars, i: int) -> CandidateSpec | None:
        """Return a :class:`CandidateSpec` if symbol ``b`` sets up at bar ``i``."""

    # --- exit (scheduled market orders) ----------------------------------
    @abstractmethod
    def exit_signal(self, pos: Position, b: Bars, i: int) -> ExitSpec | None:
        """Return an :class:`ExitSpec` to schedule a market exit, else None."""

    # --- helpers ---------------------------------------------------------
    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<{type(self).__name__} {self.name!r} {self.direction.name}>"
