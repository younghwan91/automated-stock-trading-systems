"""Optional plotting of backtest results (requires the ``plot`` extra).

Renders a three-panel tear sheet: equity curve (log scale) vs benchmark, the
underwater (drawdown) curve, and net long/short exposure over time. ``matplotlib``
is imported lazily so the core engine has no plotting dependency.
"""

from __future__ import annotations

import pandas as pd


def plot_tearsheet(
    equity: pd.DataFrame,
    benchmark: pd.Series | None = None,
    title: str = "ASTS Backtest",
    savepath: str | None = None,
    show: bool = False,
):
    """Draw an equity / drawdown / exposure tear sheet.

    Parameters
    ----------
    equity : DataFrame with a DatetimeIndex and columns ``total_equity``,
        ``long_exposure``, ``short_exposure`` (as produced by the engine).
    benchmark : optional close-price Series; rescaled to the starting equity.
    savepath : if given, the figure is written to this path (PNG/SVG/PDF).
    show : call ``plt.show()`` when True (interactive sessions).
    """
    import matplotlib

    if not show:
        matplotlib.use("Agg")  # headless-safe
    import matplotlib.pyplot as plt

    eq = equity["total_equity"].astype(float)
    running_max = eq.cummax()
    dd = (eq / running_max - 1.0) * 100.0

    fig, axes = plt.subplots(
        3, 1, figsize=(12, 9), sharex=True,
        gridspec_kw={"height_ratios": [3, 1.3, 1.3]},
    )
    ax_eq, ax_dd, ax_exp = axes

    # Panel 1 — equity vs benchmark (log scale).
    ax_eq.plot(eq.index, eq.values, color="#1565c0", lw=1.6, label="Strategy")
    if benchmark is not None:
        b = benchmark.reindex(eq.index).ffill()
        b = b / b.iloc[0] * eq.iloc[0]
        ax_eq.plot(b.index, b.values, color="#9e9e9e", lw=1.2, ls="--", label="Benchmark")
    ax_eq.set_yscale("log")
    ax_eq.set_ylabel("Equity (log)")
    ax_eq.set_title(title)
    ax_eq.legend(loc="upper left")
    ax_eq.grid(True, which="both", alpha=0.2)

    # Panel 2 — underwater / drawdown.
    ax_dd.fill_between(dd.index, dd.values, 0.0, color="#c62828", alpha=0.4)
    ax_dd.plot(dd.index, dd.values, color="#c62828", lw=0.8)
    ax_dd.set_ylabel("Drawdown %")
    ax_dd.grid(True, alpha=0.2)

    # Panel 3 — exposure.
    if {"long_exposure", "short_exposure"}.issubset(equity.columns):
        long_pct = equity["long_exposure"] / eq * 100.0
        short_pct = -equity["short_exposure"] / eq * 100.0
        ax_exp.fill_between(long_pct.index, long_pct.values, 0, color="#2e7d32", alpha=0.5, label="Long")
        ax_exp.fill_between(short_pct.index, short_pct.values, 0, color="#ad1457", alpha=0.5, label="Short")
        ax_exp.axhline(0, color="black", lw=0.6)
        ax_exp.set_ylabel("Exposure %")
        ax_exp.legend(loc="upper left", ncol=2)
        ax_exp.grid(True, alpha=0.2)
    ax_exp.set_xlabel("Date")

    fig.tight_layout()
    if savepath:
        fig.savefig(savepath, dpi=120, bbox_inches="tight")
    if show:
        plt.show()
    return fig
