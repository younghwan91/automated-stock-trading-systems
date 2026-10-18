"""README hero image: normalised equity curves of the seven systems, 2x4 small multiples.

Run from the repo root:
    uv run --with matplotlib python scripts/make_hero.py
Writes docs/images/hero-light.png and docs/images/hero-dark.png.

Data: the same synthetic universe as examples/run_suite.py (offline, reproducible).
Each panel is one system run alone at full allocation; equity is indexed to 100.
No performance numbers are printed on purpose — the picture only shows shape.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib.dates as mdates
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hero_style import caption, render_both  # noqa: E402

from asts.backtest import run_backtest  # noqa: E402
from asts.core.types import Direction  # noqa: E402
from asts.data.synthetic import make_universe  # noqa: E402
from asts.systems import SYSTEM_REGISTRY  # noqa: E402

warnings.filterwarnings("ignore")

GENERATED = "2026-10-19"
UNIVERSE = dict(n_stocks=40, start="2006-01-01", end="2018-12-31", seed=2)

# Panel titles follow the README table; (number, name, style tag).
TITLES = {
    "s1": ("System 1", "Long Trend High Momentum", "trend"),
    "s2": ("System 2", "Short RSI Thrust", "mean reversion"),
    "s3": ("System 3", "Long Mean Reversion Selloff", "mean reversion"),
    "s4": ("System 4", "Long Trend Low Volatility", "trend"),
    "s5": ("System 5", "Long High ADX Reversal", "mean reversion"),
    "s6": ("System 6", "Short High Six-Day Surge", "mean reversion"),
    "s7": ("System 7", "Catastrophe Hedge", "trend / tail risk"),
}


def run_all() -> dict[str, tuple[object, Direction]]:
    universe = make_universe(**UNIVERSE)
    curves = {}
    for key, cls in SYSTEM_REGISTRY.items():
        system = cls()
        out = run_backtest([system], universe)
        eq = out.equity["total_equity"]
        curves[key] = (eq / eq.iloc[0] * 100.0, system.direction)
    return curves


def draw(fig, axes, p, curves=None):
    axes = axes.ravel()
    for ax, key in zip(axes, TITLES):
        series, direction = curves[key]
        color = p["blue"] if direction == Direction.LONG else p["amber"]
        number, name, style = TITLES[key]
        ax.plot(series.index, series.values, color=color)
        ax.axhline(100, color=p["ink3"], linewidth=1, linestyle=":", zorder=1)
        ax.set_title(f"{number}\n{name}", fontsize=11.5, pad=6, color=p["ink"], linespacing=1.3)
        ax.text(0.0, -0.2, style, transform=ax.transAxes, ha="left", va="top",
                fontsize=9, color=p["ink3"], clip_on=False)
        ax.xaxis.set_major_locator(mdates.YearLocator(4))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.tick_params(labelsize=9.5, length=0)
        ax.margins(x=0.01)

    # Last cell: legend.
    ax = axes[-1]
    ax.set_axis_off()
    handles = [
        Line2D([0], [0], color=p["blue"], linewidth=2, label="Long systems (1, 3, 4, 5)"),
        Line2D([0], [0], color=p["amber"], linewidth=2, label="Short systems (2, 6, 7)"),
        Line2D([0], [0], color=p["ink3"], linewidth=1, linestyle=":", label="Start = 100"),
    ]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(0.0, 0.5),
              fontsize=10.5, labelcolor=p["ink2"], handlelength=2.2, borderaxespad=0)
    ax.text(0.0, 0.1, "Each system run alone, equity indexed to 100.",
            transform=ax.transAxes, fontsize=9, color=p["ink3"], ha="left", va="center")

    fig.suptitle(
        "Seven non-correlated systems, one backtester "
        "— long and short, trend and mean reversion",
        x=0.0, ha="left", fontsize=15, fontweight="bold", color=p["ink"], y=0.99,
    )
    fig.subplots_adjust(hspace=0.65, wspace=0.3, top=0.86, bottom=0.1)
    caption(
        fig,
        "Synthetic 40-stock universe, 2006-2018 (asts.data.synthetic, seed 2), the same setup as "
        f"examples/run_suite.py. Not market data, not performance. Generated {GENERATED}.",
        p,
    )


def main() -> None:
    curves = run_all()
    paths = render_both(
        lambda fig, ax, p: draw(fig, ax, p, curves=curves),
        out_dir="docs/images", name="hero", figsize=(12, 6), nrows=2, ncols=4,
    )
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
