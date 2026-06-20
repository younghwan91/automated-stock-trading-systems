"""Account state: cash, open positions, the closed-trade ledger and equity curve.

Cash convention (sign = +1 long, -1 short):

    open:   cash -= sign * shares * price        (long pays, short receives)
    close:  cash += sign * shares * price
    equity = cash + Σ sign * shares * mark_price

This makes a long position worth more as price rises and a short worth more as
price falls, which is exactly the P&L we want.
"""

from __future__ import annotations

from datetime import date

from .types import Direction, EquityPoint, Position, Trade


class Portfolio:
    def __init__(self, starting_cash: float):
        self.starting_cash = starting_cash
        self.cash = starting_cash
        self.positions: dict[tuple[str, str], Position] = {}
        self.closed_trades: list[Trade] = []
        self.equity_curve: list[EquityPoint] = []

    # --- mutation --------------------------------------------------------
    def open(
        self,
        *,
        system: str,
        symbol: str,
        direction: Direction,
        shares: int,
        dt: date,
        price: float,
        initial_stop: float,
        atr: float,
        trail_pct: float | None,
        commission: float,
    ) -> Position:
        self.cash -= direction.sign * shares * price
        self.cash -= commission
        pos = Position(
            system=system,
            symbol=symbol,
            direction=direction,
            shares=shares,
            entry_date=dt,
            entry_price=price,
            initial_stop=initial_stop,
            atr_at_entry=atr,
            trail_pct=trail_pct,
            extreme_close=price,
            bars_held=0,
        )
        self.positions[(system, symbol)] = pos
        return pos

    def close(
        self,
        key: tuple[str, str],
        *,
        dt: date,
        price: float,
        reason: str,
        commission: float,
    ) -> Trade:
        pos = self.positions.pop(key)
        sign = pos.direction.sign
        self.cash += sign * pos.shares * price
        self.cash -= commission
        pnl = (price - pos.entry_price) * pos.shares * sign - commission
        ret = (price - pos.entry_price) / pos.entry_price * sign
        trade = Trade(
            system=pos.system,
            symbol=pos.symbol,
            direction=pos.direction,
            shares=pos.shares,
            entry_date=pos.entry_date,
            exit_date=dt,
            entry_price=pos.entry_price,
            exit_price=price,
            pnl=pnl,
            return_pct=ret,
            bars_held=pos.bars_held,
            exit_reason=reason,
        )
        self.closed_trades.append(trade)
        return trade

    # --- valuation -------------------------------------------------------
    def equity(self, mark: dict[str, float]) -> float:
        total = self.cash
        for pos in self.positions.values():
            px = mark.get(pos.symbol, pos.entry_price)
            total += pos.direction.sign * pos.shares * px
        return total

    def exposures(self, mark: dict[str, float]) -> tuple[float, float]:
        long_exp = short_exp = 0.0
        for pos in self.positions.values():
            px = mark.get(pos.symbol, pos.entry_price)
            val = pos.shares * px
            if pos.direction is Direction.LONG:
                long_exp += val
            else:
                short_exp += val
        return long_exp, short_exp

    def record_equity(self, dt: date, mark: dict[str, float]) -> None:
        eq = self.equity(mark)
        long_exp, short_exp = self.exposures(mark)
        self.equity_curve.append(
            EquityPoint(
                dt=dt,
                total_equity=eq,
                cash=self.cash,
                long_exposure=long_exp,
                short_exposure=short_exp,
                open_positions=len(self.positions),
            )
        )

    def has(self, system: str, symbol: str) -> bool:
        return (system, symbol) in self.positions
