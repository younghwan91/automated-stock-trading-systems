"""Monte Carlo resampling of the equity curve's daily returns.

A single backtest is one realised path; it conflates edge with luck. By
resampling the strategy's daily returns we generate a distribution of plausible
alternative histories and read off the tail risks the point estimate hides:
the spread of CAGR, the distribution of maximum drawdown, the probability of a
drawdown worse than some threshold, and the probability of finishing underwater.

Two resampling schemes:

* **iid** — draw daily returns independently with replacement. Simple, but
  destroys autocorrelation (and therefore understates drawdown clustering).
* **block** — draw contiguous blocks of ``block`` days (a stationary block
  bootstrap). Preserves short-horizon autocorrelation, giving more realistic
  drawdowns. This is the default.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252


@dataclass
class MonteCarloResult:
    n_sims: int
    horizon_days: int
    method: str
    cagr: np.ndarray            # per-sim annualised return (fraction)
    max_drawdown: np.ndarray    # per-sim max drawdown (negative fraction)
    total_return: np.ndarray    # per-sim terminal return (fraction)

    def percentiles(self, ps=(5, 25, 50, 75, 95)) -> pd.DataFrame:
        rows = {}
        for label, arr in (
            ("cagr_pct", self.cagr * 100),
            ("max_drawdown_pct", self.max_drawdown * 100),
            ("total_return_pct", self.total_return * 100),
        ):
            rows[label] = {f"p{p}": float(np.percentile(arr, p)) for p in ps}
        return pd.DataFrame(rows).T

    def prob_drawdown_worse_than(self, threshold_pct: float) -> float:
        """Probability that max drawdown is worse than ``threshold_pct`` (e.g. 20)."""
        return float(np.mean(self.max_drawdown <= -abs(threshold_pct) / 100.0))

    def prob_negative_return(self) -> float:
        return float(np.mean(self.total_return < 0.0))

    def summary(self) -> str:
        pctl = self.percentiles()
        lines = [
            f"Monte Carlo ({self.n_sims} sims, {self.method} bootstrap, "
            f"{self.horizon_days} days)",
            "-" * 56,
            pctl.round(2).to_string(),
            "",
            f"P(maxDD worse than -20%) : {self.prob_drawdown_worse_than(20) * 100:.1f}%",
            f"P(maxDD worse than -30%) : {self.prob_drawdown_worse_than(30) * 100:.1f}%",
            f"P(negative total return) : {self.prob_negative_return() * 100:.1f}%",
        ]
        return "\n".join(lines)


def _max_drawdown(equity: np.ndarray) -> float:
    running_max = np.maximum.accumulate(equity)
    return float((equity / running_max - 1.0).min())


def monte_carlo_equity(
    equity: pd.DataFrame | pd.Series,
    n_sims: int = 2000,
    method: str = "block",
    block: int = 10,
    horizon_days: int | None = None,
    seed: int = 0,
) -> MonteCarloResult:
    """Resample daily returns of an equity curve into ``n_sims`` synthetic paths.

    ``equity`` may be the engine's equity DataFrame (uses ``total_equity``) or a
    bare equity Series.
    """
    if isinstance(equity, pd.DataFrame):
        eq = equity["total_equity"].astype(float)
    else:
        eq = equity.astype(float)
    returns = eq.pct_change().dropna().to_numpy()
    if returns.size < 2:
        raise ValueError("need at least two equity observations")

    horizon = horizon_days or returns.size
    rng = np.random.default_rng(seed)

    cagr = np.empty(n_sims)
    mdd = np.empty(n_sims)
    tot = np.empty(n_sims)
    years = horizon / TRADING_DAYS

    for s in range(n_sims):
        if method == "iid":
            sample = rng.choice(returns, size=horizon, replace=True)
        elif method == "block":
            sample = _block_sample(returns, horizon, block, rng)
        else:
            raise ValueError(f"unknown method {method!r} (use 'iid' or 'block')")
        path = np.cumprod(1.0 + sample)
        terminal = path[-1]
        tot[s] = terminal - 1.0
        cagr[s] = terminal ** (1.0 / years) - 1.0
        mdd[s] = _max_drawdown(np.concatenate([[1.0], path]))

    return MonteCarloResult(
        n_sims=n_sims, horizon_days=horizon, method=method,
        cagr=cagr, max_drawdown=mdd, total_return=tot,
    )


def _block_sample(returns: np.ndarray, horizon: int, block: int, rng) -> np.ndarray:
    n = returns.size
    out = np.empty(horizon)
    filled = 0
    while filled < horizon:
        start = rng.integers(0, n)
        take = min(block, horizon - filled)
        idx = (start + np.arange(take)) % n  # wrap-around (stationary bootstrap)
        out[filled : filled + take] = returns[idx]
        filled += take
    return out
