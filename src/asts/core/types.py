"""Core value objects shared across the engine.

These are intentionally small, typed dataclasses so the rest of the engine can
stay declarative. Money is tracked in account currency; shares are integers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class Direction(Enum):
    LONG = 1
    SHORT = -1

    @property
    def sign(self) -> int:
        return self.value


class Style(Enum):
    TREND = "trend_following"
    MEAN_REVERSION = "mean_reversion"


class OrderType(Enum):
    MARKET_ON_OPEN = "MOO"
    MARKET_ON_CLOSE = "MOC"
    LIMIT = "LIMIT"  # buy: at/below price; short: at/above price


@dataclass(slots=True)
class EntryOrder:
    """An entry order created at the close of day D, executed on day D+1."""

    system: str
    symbol: str
    direction: Direction
    order_type: OrderType
    shares: int
    limit_price: float | None  # None for market orders
    stop_atr_mult: float  # multiple of ATR used to derive the protective stop
    atr_at_signal: float  # ATR value captured at signal time
    rank_value: float
    reference_price: float  # price used for sizing (limit price or last close)


@dataclass(slots=True)
class ExitOrder:
    """A scheduled market exit (created at close of D, executed on D+1)."""

    system: str
    symbol: str
    order_type: OrderType  # MOO or MOC
    reason: str


@dataclass(slots=True)
class Position:
    system: str
    symbol: str
    direction: Direction
    shares: int
    entry_date: date
    entry_price: float
    initial_stop: float
    atr_at_entry: float
    trail_pct: float | None = None
    # high-water mark of close used for trailing stops (long) / low-water (short)
    extreme_close: float = 0.0
    bars_held: int = 0

    @property
    def cost_basis(self) -> float:
        return self.entry_price * self.shares

    def market_value(self, price: float) -> float:
        return price * self.shares

    def unrealized_pnl(self, price: float) -> float:
        return (price - self.entry_price) * self.shares * self.direction.sign


@dataclass(slots=True)
class Trade:
    """A closed round-trip, recorded for analytics."""

    system: str
    symbol: str
    direction: Direction
    shares: int
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    pnl: float
    return_pct: float
    bars_held: int
    exit_reason: str

    @property
    def is_winner(self) -> bool:
        return self.pnl > 0.0


@dataclass(slots=True)
class EquityPoint:
    dt: date
    total_equity: float
    cash: float
    long_exposure: float
    short_exposure: float
    open_positions: int


@dataclass(slots=True)
class SizingParams:
    """Position-sizing configuration (Bensdorp defaults)."""

    risk_pct: float = 0.02          # percent-risk per trade
    max_pct_size: float = 0.10      # percent-size cap per position
    max_positions: int = 10         # per system
    allocation: float = 1.0         # fraction of total equity assigned to system


@dataclass(slots=True)
class Fill:
    symbol: str
    shares: int
    price: float
    direction: Direction
    is_entry: bool
    reason: str = ""
