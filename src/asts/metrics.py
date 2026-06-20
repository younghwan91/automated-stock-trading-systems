"""Performance analytics computed from an equity curve and the trade ledger.

The metrics mirror the statistics the book reports for every system: CAGR,
maximum drawdown, MAR, Sharpe, annualised volatility, win rate, win/loss
(payoff) ratio, average bars in trade, exposure and the longest drawdown.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252


@dataclass
class Metrics:
    start: str
    end: str
    years: float
    starting_equity: float
    ending_equity: float
    total_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    longest_drawdown_days: int
    mar: float
    sharpe: float
    volatility_pct: float
    num_trades: int
    win_rate_pct: float
    win_loss_ratio: float
    avg_win_pct: float
    avg_loss_pct: float
    avg_bars_held: float
    exposure_pct: float
    benchmark_corr: float

    def as_dict(self) -> dict:
        return asdict(self)


def _drawdown_series(equity: pd.Series) -> pd.Series:
    running_max = equity.cummax()
    return equity / running_max - 1.0


def longest_drawdown_days(equity: pd.Series) -> int:
    """Longest stretch (in calendar days) spent below a prior peak."""
    running_max = equity.cummax()
    underwater = equity < running_max
    longest = 0
    start = None
    idx = equity.index
    for i, uw in enumerate(underwater.to_numpy()):
        if uw and start is None:
            start = idx[i - 1] if i > 0 else idx[i]
        elif not uw and start is not None:
            longest = max(longest, (idx[i] - start).days)
            start = None
    if start is not None:
        longest = max(longest, (idx[-1] - start).days)
    return int(longest)


def compute_metrics(
    equity_df: pd.DataFrame,
    trades: list,
    benchmark: pd.Series | None = None,
) -> Metrics:
    """``equity_df`` must have a DatetimeIndex and a ``total_equity`` column."""
    eq = equity_df["total_equity"].astype(float)
    eq = eq[~eq.index.duplicated(keep="last")].sort_index()

    start, end = eq.index[0], eq.index[-1]
    years = max((end - start).days / 365.25, 1e-9)
    starting_equity = float(eq.iloc[0])
    ending_equity = float(eq.iloc[-1])
    total_return = ending_equity / starting_equity - 1.0
    cagr = (ending_equity / starting_equity) ** (1.0 / years) - 1.0

    dd = _drawdown_series(eq)
    max_dd = float(dd.min())

    daily_ret = eq.pct_change().dropna()
    vol = float(daily_ret.std(ddof=1) * np.sqrt(TRADING_DAYS)) if len(daily_ret) > 1 else 0.0
    sharpe = (
        float(daily_ret.mean() / daily_ret.std(ddof=1) * np.sqrt(TRADING_DAYS))
        if len(daily_ret) > 1 and daily_ret.std(ddof=1) > 0
        else 0.0
    )
    mar = cagr / abs(max_dd) if max_dd != 0 else 0.0

    # Trade statistics
    n = len(trades)
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    win_rate = len(wins) / n if n else 0.0
    avg_win = float(np.mean([t.return_pct for t in wins])) if wins else 0.0
    avg_loss = float(np.mean([t.return_pct for t in losses])) if losses else 0.0
    avg_win_dollars = float(np.mean([t.pnl for t in wins])) if wins else 0.0
    avg_loss_dollars = float(np.mean([abs(t.pnl) for t in losses])) if losses else 0.0
    win_loss_ratio = avg_win_dollars / avg_loss_dollars if avg_loss_dollars else 0.0
    avg_bars = float(np.mean([t.bars_held for t in trades])) if n else 0.0

    # Exposure: fraction of days holding at least one position.
    exposure = (
        float((equity_df["open_positions"] > 0).mean()) if "open_positions" in equity_df else 0.0
    )

    corr = 0.0
    if benchmark is not None and len(daily_ret) > 2:
        b = benchmark.reindex(eq.index).pct_change().dropna()
        joined = pd.concat([daily_ret, b], axis=1, join="inner").dropna()
        if len(joined) > 2 and joined.iloc[:, 1].std() > 0:
            corr = float(joined.iloc[:, 0].corr(joined.iloc[:, 1]))

    return Metrics(
        start=str(start.date()),
        end=str(end.date()),
        years=round(years, 2),
        starting_equity=round(starting_equity, 2),
        ending_equity=round(ending_equity, 2),
        total_return_pct=round(total_return * 100, 2),
        cagr_pct=round(cagr * 100, 2),
        max_drawdown_pct=round(max_dd * 100, 2),
        longest_drawdown_days=longest_drawdown_days(eq),
        mar=round(mar, 2),
        sharpe=round(sharpe, 2),
        volatility_pct=round(vol * 100, 2),
        num_trades=n,
        win_rate_pct=round(win_rate * 100, 2),
        win_loss_ratio=round(win_loss_ratio, 2),
        avg_win_pct=round(avg_win * 100, 2),
        avg_loss_pct=round(avg_loss * 100, 2),
        avg_bars_held=round(avg_bars, 1),
        exposure_pct=round(exposure * 100, 2),
        benchmark_corr=round(corr, 3),
    )


def format_metrics(m: Metrics) -> str:
    d = m.as_dict()
    label = {
        "start": "Start", "end": "End", "years": "Years",
        "starting_equity": "Starting Equity", "ending_equity": "Ending Equity",
        "total_return_pct": "Total Return %", "cagr_pct": "CAGR %",
        "max_drawdown_pct": "Max Drawdown %", "longest_drawdown_days": "Longest DD (days)",
        "mar": "MAR", "sharpe": "Sharpe", "volatility_pct": "Volatility %",
        "num_trades": "Trades", "win_rate_pct": "Win Rate %",
        "win_loss_ratio": "Win/Loss Ratio", "avg_win_pct": "Avg Win %",
        "avg_loss_pct": "Avg Loss %", "avg_bars_held": "Avg Bars Held",
        "exposure_pct": "Exposure %", "benchmark_corr": "Benchmark Corr",
    }
    width = max(len(v) for v in label.values())
    lines = ["Performance Summary", "-" * (width + 18)]
    for k, v in d.items():
        lines.append(f"{label[k]:<{width}} : {v}")
    return "\n".join(lines)
