"""Event-driven daily backtest engine.

Execution model (matches the book's "next day" semantics):

For each trading day ``d`` (the master calendar is the market/SPY calendar):

1. **Fill** orders generated at the *previous* close using day ``d``'s bars:
   limit/market entries and scheduled market-on-open exits.
2. **Protective stops** — for positions opened *before* ``d`` (stops are placed
   "the day after entering"), check the ATR stop-loss and trailing stop against
   day ``d``'s range; an intraday stop pre-empts any same-day MOC exit.
3. **Market-on-close exits** scheduled yesterday are filled at today's close.
4. **Signals at the close of ``d``** — advance ``bars_held``, update trailing
   high-water marks, evaluate each system's ``exit_signal`` (schedule market
   exits for ``d+1``) and scan the universe for new setups (schedule entries
   for ``d+1``), respecting per-system position limits.
5. **Mark to market** and append to the equity curve.

Sizing uses the equity marked at the close of ``d`` (the signal day), times the
system's capital allocation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ..systems import build_suite
from .position_sizing import calculate_shares
from .portfolio import Portfolio
from .system import Bars, TradingSystem
from .types import Direction, EntryOrder, ExitOrder, OrderType


@dataclass
class BacktestConfig:
    starting_equity: float = 100_000.0
    slippage_pct: float = 0.0          # adverse fraction applied to fills
    commission_per_trade: float = 0.0  # flat $ per fill
    warmup_bars: int = 200             # skip until indicators are populated


@dataclass
class BacktestResult:
    equity_curve: "object"             # pandas.DataFrame (set by runner)
    trades: list = field(default_factory=list)
    portfolio: Portfolio | None = None
    systems: list = field(default_factory=list)


class BacktestEngine:
    def __init__(
        self,
        systems: list[TradingSystem],
        bars: dict[str, Bars],
        market_symbol: str = "SPY",
        config: BacktestConfig | None = None,
    ):
        if market_symbol not in bars:
            raise ValueError(f"market symbol {market_symbol!r} not present in data")
        self.systems = systems
        self.bars = bars
        self.market_symbol = market_symbol
        self.cfg = config or BacktestConfig()
        self.market = bars[market_symbol]
        self.pf = Portfolio(self.cfg.starting_equity)

        # Per-symbol date -> index maps for O(1) calendar alignment.
        self._index_of: dict[str, dict] = {
            sym: {d: i for i, d in enumerate(b.dates)} for sym, b in bars.items()
        }
        self.calendar = list(self.market.dates)

        # Pending orders keyed for execution on the following day.
        self._pending_entries: list[EntryOrder] = []
        self._pending_exits: list[ExitOrder] = []

    # -- fill helpers -----------------------------------------------------
    def _slip_buy(self, price: float) -> float:
        return price * (1.0 + self.cfg.slippage_pct)

    def _slip_sell(self, price: float) -> float:
        return price * (1.0 - self.cfg.slippage_pct)

    def _bars_idx(self, symbol: str, dt) -> int | None:
        return self._index_of.get(symbol, {}).get(dt)

    # -- order execution --------------------------------------------------
    def _execute_entries(self, dt) -> None:
        for order in self._pending_entries:
            b = self.bars[order.symbol]
            i = self._bars_idx(order.symbol, dt)
            if i is None:
                continue  # symbol did not trade today; order expires
            if self.pf.has(order.system, order.symbol):
                continue  # already in this name for this system
            o, h, l, c = b.open[i], b.high[i], b.low[i], b.close[i]
            fill = None
            if order.order_type is OrderType.MARKET_ON_OPEN:
                fill = o
            elif order.order_type is OrderType.LIMIT:
                lim = order.limit_price
                if order.direction is Direction.LONG:
                    if l <= lim:                       # touched our buy limit
                        fill = min(o, lim)
                else:  # SHORT sell-limit
                    if h >= lim:
                        fill = max(o, lim)
            if fill is None or math.isnan(fill):
                continue

            if order.direction is Direction.LONG:
                fill = self._slip_buy(fill)
                stop = fill - order.stop_atr_mult * order.atr_at_signal
            else:
                fill = self._slip_sell(fill)
                stop = fill + order.stop_atr_mult * order.atr_at_signal

            sys = self._system_by_name(order.system)
            self.pf.open(
                system=order.system,
                symbol=order.symbol,
                direction=order.direction,
                shares=order.shares,
                dt=dt,
                price=fill,
                initial_stop=stop,
                atr=order.atr_at_signal,
                trail_pct=sys.trail_pct,
                commission=self.cfg.commission_per_trade,
            )
        self._pending_entries.clear()

    def _execute_scheduled_exits(self, dt, when: OrderType) -> None:
        """Fill MOO exits at the open or MOC exits at the close."""
        remaining: list[ExitOrder] = []
        for order in self._pending_exits:
            if order.order_type is not when:
                remaining.append(order)
                continue
            key = (order.system, order.symbol)
            if key not in self.pf.positions:
                continue  # already closed (e.g. stopped out intraday)
            i = self._bars_idx(order.symbol, dt)
            if i is None:
                remaining.append(order)  # try again next day it trades
                continue
            b = self.bars[order.symbol]
            px = b.open[i] if when is OrderType.MARKET_ON_OPEN else b.close[i]
            pos = self.pf.positions[key]
            px = self._slip_sell(px) if pos.direction is Direction.LONG else self._slip_buy(px)
            self.pf.close(
                key, dt=dt, price=px, reason=order.reason,
                commission=self.cfg.commission_per_trade,
            )
        self._pending_exits = remaining

    def _check_protective_stops(self, dt) -> None:
        for key in list(self.pf.positions.keys()):
            pos = self.pf.positions[key]
            if pos.entry_date >= dt:
                continue  # stop active only the day after entry
            i = self._bars_idx(pos.symbol, dt)
            if i is None:
                continue
            b = self.bars[pos.symbol]
            o, h, l = b.open[i], b.high[i], b.low[i]
            if pos.direction is Direction.LONG:
                stop = pos.initial_stop
                if pos.trail_pct is not None:
                    stop = max(stop, pos.extreme_close * (1.0 - pos.trail_pct))
                if l <= stop:
                    fill = self._slip_sell(min(o, stop))
                    self.pf.close(key, dt=dt, price=fill, reason="stop_loss",
                                  commission=self.cfg.commission_per_trade)
            else:  # SHORT — buy-stop above
                stop = pos.initial_stop
                if pos.trail_pct is not None:
                    stop = min(stop, pos.extreme_close * (1.0 + pos.trail_pct))
                if h >= stop:
                    fill = self._slip_buy(max(o, stop))
                    self.pf.close(key, dt=dt, price=fill, reason="stop_loss",
                                  commission=self.cfg.commission_per_trade)

    # -- signal generation (at the close) ---------------------------------
    def _generate_signals(self, dt, mark: dict[str, float]) -> None:
        total_equity = self.pf.equity(mark)

        # Advance holding state, update trailing extremes, schedule exits.
        for key, pos in list(self.pf.positions.items()):
            i = self._bars_idx(pos.symbol, dt)
            if i is None:
                continue
            b = self.bars[pos.symbol]
            pos.bars_held += 1
            c = b.close[i]
            if pos.direction is Direction.LONG:
                pos.extreme_close = max(pos.extreme_close, c)
            else:
                pos.extreme_close = min(pos.extreme_close, c)
            sys = self._system_by_name(pos.system)
            spec = sys.exit_signal(pos, b, i)
            if spec is not None:
                self._pending_exits.append(
                    ExitOrder(pos.system, pos.symbol, spec.order_type, spec.reason)
                )

        # Scan for new entries, per system, respecting position limits.
        mi = self._bars_idx(self.market_symbol, dt)
        for sys in self.systems:
            if mi is None or not sys.market_filter(self.market, mi):
                continue
            open_count = sum(1 for (s, _), p in self.pf.positions.items() if s == sys.name)
            scheduled = sum(1 for o in self._pending_entries if o.system == sys.name)
            slots = sys.sizing.max_positions - open_count - scheduled
            if slots <= 0:
                continue

            candidates = []
            for sym, b in self.bars.items():
                if self.pf.has(sys.name, sym):
                    continue
                i = self._bars_idx(sym, dt)
                if i is None or i < self.cfg.warmup_bars:
                    continue
                spec = sys.entry_signal(b, i)
                if spec is None:
                    continue
                candidates.append((spec.rank_value, sym, spec))

            if not candidates:
                continue
            candidates.sort(key=lambda t: t[0], reverse=True)

            for _, sym, spec in candidates[:slots]:
                shares = calculate_shares(
                    total_equity=total_equity,
                    reference_price=spec.reference_price,
                    atr=spec.atr,
                    stop_atr_mult=spec.stop_atr_mult,
                    params=sys.sizing,
                )
                if shares <= 0:
                    continue
                self._pending_entries.append(
                    EntryOrder(
                        system=sys.name,
                        symbol=sym,
                        direction=sys.direction,
                        order_type=spec.order_type,
                        shares=shares,
                        limit_price=spec.limit_price,
                        stop_atr_mult=spec.stop_atr_mult,
                        atr_at_signal=spec.atr,
                        rank_value=spec.rank_value,
                        reference_price=spec.reference_price,
                    )
                )

    def _system_by_name(self, name: str) -> TradingSystem:
        for s in self.systems:
            if s.name == name:
                return s
        raise KeyError(name)

    def _mark_prices(self, dt) -> dict[str, float]:
        mark: dict[str, float] = {}
        for key, pos in self.pf.positions.items():
            i = self._bars_idx(pos.symbol, dt)
            if i is not None:
                mark[pos.symbol] = self.bars[pos.symbol].close[i]
        return mark

    # -- main loop --------------------------------------------------------
    def run(self) -> Portfolio:
        for dt in self.calendar:
            self._execute_scheduled_exits(dt, OrderType.MARKET_ON_OPEN)
            self._execute_entries(dt)
            self._check_protective_stops(dt)
            self._execute_scheduled_exits(dt, OrderType.MARKET_ON_CLOSE)

            mark = self._mark_prices(dt)
            self._generate_signals(dt, mark)
            self.pf.record_equity(dt, self._mark_prices(dt))
        return self.pf
